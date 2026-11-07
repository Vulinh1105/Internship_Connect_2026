from hashlib import sha256
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select
from app.common.records import first,record,require
from app.common import storage,file_parsing
from app.ai.providers.embedding import normalize,words
from app.ai.providers.llm import structured
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
    return record(get_own(db,actor))

def public_name(db,ident):
    s=require(repo.get_student(db,ident))
    return s.name

def user_id_for(db,ident):
    return require(repo.get_student(db,ident)).user_id

def match_input(db,student_id,cv_id=None):
    s=require(repo.get_student(db,student_id))
    options=select(CV).where(CV.student_id==s.id,CV.confirmed.is_(True))
    if cv_id is not None:
        options=options.where(CV.id==cv_id)
    cv=db.scalar(options.order_by(CV.id.desc()).limit(1))
    if cv:
        content=" ".join(cv.extracted.get("projects",[])+cv.extracted.get("experience",[]))
    else:
        content=s.summary
    safe=file_parsing.redact(content,s.name)[:4000]
    skills=s.skills
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
    return record(cv,"id","original_name","extracted","confirmed","created_at")

def list_cvs(db,actor):
    s=get_own(db,actor)
    return [view_cv(c) for c in db.scalars(select(CV).filter_by(student_id=s.id).order_by(CV.id.desc()))]

def own_cv(db,actor,ident):
    s=get_own(db,actor)
    return require(first(db,CV,id=ident,student_id=s.id),"Không tìm thấy CV của bạn")

def upload(db,actor,name,data,ai_consent):
    s=get_own(db,actor)
    digest=sha256(data).hexdigest()
    previous=first(db,CV,student_id=s.id,content_hash=digest)
    if previous:
        return view_cv(previous)
    key=storage.save(data,name,folder="cvs",allowed={".pdf",".docx",".txt"},max_bytes=5_000_000)
    path=storage.resolve(key)
    try:
        safe=file_parsing.redact(file_parsing.parse(path),s.name)
        normal=normalize(safe)
        known=[v["name"] for v in skills_catalog(db) if set(words(v["name"])) and normalize(v["name"]) in normal]
        fallback=CVFacts(skills=known).model_dump()
        extracted=structured(CVFacts,"Trích xuất các mục được nêu trong CV, không bổ sung thông tin.",
                             {"cv":safe},fallback,user_id=actor["id"],feature="cv_extract") if ai_consent else CVFacts(**fallback)
        facts=extracted.model_dump()
        facts["skills"],facts["pending_skills"]=canonical(db,facts["skills"])
        cv=CV(student_id=s.id,original_name=Path(name).name[:255],storage_key=key,parsed_text=safe,
              content_hash=digest,extracted=facts,confirmed=False)
        db.add(cv)
        db.commit()
        return view_cv(cv)
    except Exception:
        path.unlink(missing_ok=True)
        raise

def confirm(db,actor,ident,facts):
    from app.ai.vector.sync import enqueue
    s=get_own(db,actor)
    cv=own_cv(db,actor,ident)
    values=facts.model_dump()
    values["skills"],unknown=canonical(db,values["skills"])
    values["pending_skills"]=unknown
    cv.extracted=values
    cv.confirmed=True
    s.skills=list(dict.fromkeys(s.skills+values["skills"]))
    s.details={**s.details,"cv_facts":values,"pending_skills":unknown}
    enqueue(db,"cvs",cv.id)
    db.commit()
    return view_cv(cv)

def vector_record(db,ident):
    c=repo.get_cv(db,ident)
    if not c or not c.confirmed:
        return None
    s=require(repo.get_student(db,c.student_id))
    parts=c.extracted.get("skills",[])+c.extracted.get("projects",[])+c.extracted.get("experience",[])
    return {"text":file_parsing.redact(" ".join(parts),s.name)[:8000],"user_id":s.user_id}

def file_for_student(db,student_id,cv_id):
    cv=require(first(db,CV,id=cv_id,student_id=student_id),"Không tìm thấy CV")
    return storage.resolve(cv.storage_key),cv.original_name

def confirmed_cv_ids(db):
    return set(db.scalars(select(CV.id).where(CV.confirmed.is_(True))))
