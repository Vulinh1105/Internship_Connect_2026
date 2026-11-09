from hashlib import sha256
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select, update
from app.common.records import first,record,require
from app.common import storage,file_parsing
from app.ai.providers.embedding import normalize,words
from app.core.config import now
from sqlalchemy.exc import IntegrityError
from .models import Student,Skill,CV
from .schemas import CVFacts
from . import repository as repo

ALIASES={"reactjs":"react","react.js":"react","nodejs":"node.js","powerbi":"power bi","postgres":"postgresql"}

def create_profile(db,user_id,name):
    student=Student(user_id=user_id,name=name,major="",summary="",skills=[],preferences={},details={})
    db.add(student)
    db.flush()
    return student.id

def get_own(db,actor):
    if actor["role"]!="student":
        raise HTTPException(403,"Chỉ sinh viên có hồ sơ cá nhân")
    return require(first(db,Student,user_id=actor["id"]),"Chưa có hồ sơ sinh viên")

def profile(db,actor):
    student=get_own(db,actor)
    return {**record(student),"skills":match_input(db,student.id)["skills"]}

def public_name(db,ident):
    s=require(repo.get_student(db,ident))
    return s.name

def applicant_view(db,student_id,cv_id=None):
    # Phần hồ sơ sinh viên mà doanh nghiệp được xem trên đơn ứng tuyển: chỉ ngành học và kỹ năng.
    info=match_input(db,student_id,cv_id)
    return {"major":info["major"],"skills":info["skills"]}

def user_id_for(db,ident):
    return require(repo.get_student(db,ident)).user_id

def match_input(db,student_id,cv_id=None):
    s=require(repo.get_student(db,student_id))
    options=select(CV).where(CV.student_id==s.id,CV.confirmed.is_(True),CV.archived.is_(False))
    if cv_id is not None:
        options=options.where(CV.id==cv_id)
    cv=db.scalar(options.order_by(CV.created_at.desc(),CV.id.desc()).limit(1))
    if cv:
        content=cv_text(cv)
        skills=cv.extracted.get("skills",[])
    else:
        archived=db.scalars(select(CV.extracted).filter_by(student_id=s.id,archived=True))
        archived_skills={skill for facts in archived for skill in facts.get("skills",[])}
        skills=[skill for skill in s.skills if skill not in archived_skills]
        content=s.summary
    safe=file_parsing.redact(content,s.name)[:4000]
    return {"student_id":s.id,"major":s.major,"skills":skills,"preferences":s.preferences,
            "text":" ".join([s.major, s.preferences.get("target_category","")," ".join(skills),safe]),
            "cv_id":cv.id if cv else None}

def skills_catalog(db):
    return [record(s) for s in db.scalars(select(Skill).order_by(Skill.name))]

def canonical(db,items):
    table={normalize(s.name):s.name for s in db.scalars(select(Skill))}
    known=[]; unknown=[]
    for name in items:
        clean=name.strip()[:100]
        if not clean:
            continue
        code=normalize(clean)
        value=table.get(ALIASES.get(code,code))
        target=known if value else unknown
        if (value or clean) not in target:
            target.append(value or clean)
    return known,unknown

def update_profile(db,actor,data):
    s=get_own(db,actor)
    s.name=data.name.strip()
    s.major=data.major.strip()
    s.summary=data.summary
    s.skills,unknown=canonical(db,data.skills)
    s.preferences=data.preferences.model_dump()
    s.details={**s.details,"pending_skills":unknown}
    db.commit()
    return record(s)

def view_cv(cv):
    return {**record(cv,"id","original_name","extracted","confirmed","created_at"),"has_text":bool(cv.parsed_text.strip())}

def list_cvs(db,actor):
    s=get_own(db,actor)
    return [view_cv(c) for c in db.scalars(select(CV).filter_by(student_id=s.id,archived=False).order_by(CV.created_at.desc(),CV.id.desc()))]

def own_cv(db,actor,ident):
    s=get_own(db,actor)
    return require(first(db,CV,id=ident,student_id=s.id,archived=False),"Không tìm thấy CV của bạn")

def archive_cv(db,cv):
    from app.ai.vector.sync import enqueue
    changed=db.execute(update(CV).where(CV.id==cv.id,CV.archived.is_(False)).values(archived=True))
    if changed.rowcount!=1:
        raise HTTPException(409,"CV vừa thay đổi. Hãy tải lại trang.")
    enqueue(db,"cvs",cv.id)


def remove_cv(db,actor,ident):
    archive_cv(db,own_cv(db,actor,ident))
    db.commit()


def upload(db,actor,name,data,*,replace_id=None):
    from app.ai.vector.sync import enqueue
    s=get_own(db,actor)
    old=own_cv(db,actor,replace_id) if replace_id is not None else None
    digest=sha256(data).hexdigest()
    cv=first(db,CV,student_id=s.id,content_hash=digest)
    path=None
    try:
        if cv is None:
            key=storage.save(data,name,folder="cvs",allowed={".pdf",".docx",".txt"},max_bytes=5_000_000)
            path=storage.resolve(key)
            safe=file_parsing.redact(file_parsing.parse(path,allow_empty_pdf=True),s.name)[:15_000]
            terms=" "+" ".join(words(safe))+" "
            skills=[v["name"] for v in skills_catalog(db)
                    if (tokens:=words(v["name"])) and (" "+" ".join(tokens)+" ") in terms]
            cv=CV(student_id=s.id,original_name=Path(name).name[:255],storage_key=key,parsed_text=safe,
                  content_hash=digest,extracted=CVFacts(skills=skills[:40]).model_dump())
            db.add(cv)
        if old is not None and old.id!=cv.id:
            archive_cv(db,old)
        if cv.archived or (old is not None and old.id!=cv.id):
            cv.created_at=now()
        cv.archived=False
        cv.confirmed=True
        db.flush()
        enqueue(db,"cvs",cv.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        if path is not None:
            path.unlink(missing_ok=True)
        if isinstance(exc,IntegrityError):
            raise HTTPException(409,"CV vừa được cập nhật. Hãy tải lại trang và thử lại.") from exc
        raise
    return view_cv(cv)


def confirm(db,actor,ident,facts):
    from app.ai.vector.sync import enqueue
    cv=own_cv(db,actor,ident)
    values=facts.model_dump()
    values["skills"],unknown=canonical(db,values["skills"])
    values["pending_skills"]=unknown
    cv.extracted=values
    cv.confirmed=True
    enqueue(db,"cvs",cv.id)
    db.commit()
    return view_cv(cv)

def cv_text(cv):
    return " ".join(cv.extracted.get("projects",[])+cv.extracted.get("experience",[])) or cv.parsed_text


def vector_record(db,ident):
    c=repo.get_cv(db,ident)
    if not c or not c.confirmed or c.archived:
        return None
    s=require(repo.get_student(db,c.student_id))
    parts=c.extracted.get("skills",[])+[cv_text(c)]
    text=file_parsing.redact(" ".join(parts),s.name).strip()[:8000]
    return {"text":text,"user_id":s.user_id} if text else None

def file_for_student(db,student_id,cv_id,*,submitted=False):
    cv=first(db,CV,id=cv_id,student_id=student_id)
    if cv is None or (cv.archived and not submitted):
        raise HTTPException(404,"Không tìm thấy CV")
    return storage.resolve(cv.storage_key),cv.original_name

def confirmed_cv_ids(db):
    return set(db.scalars(select(CV.id).where(CV.confirmed.is_(True),CV.archived.is_(False))))
