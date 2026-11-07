from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import now, today
from app.common.pagination import page
from app.common.records import first, put, record, require
from app.modules.companies import service as companies
from . import repository as repo
from .models import Job, Review, SavedJob
from .moderation import assess

def is_public(j):
    return (j.status == "open" and j.moderation_status == "approved" and j.deleted_at is None
            and (j.deadline is None or j.deadline >= today()))

def output(db, j):
    return {**record(j), "company_name": companies.company_name(db, j.company_id), "active": is_public(j)}

def search(db, **filters):
    rows, total = repo.find(db, **filters)
    return page([output(db,j) for j in rows],filters.get("offset",0),filters.get("limit",20),total)

def detail(db, ident, actor=None):
    j = require(repo.get_job(db, ident), "Không tìm thấy tin")
    if not is_public(j):
        if not actor or (actor["role"] not in {"staff","admin"} and j.company_id not in companies.memberships(db,actor["id"])):
            raise HTTPException(404, "Tin không công khai hoặc đã hết hạn")
    return output(db,j)

def public_detail(db, ident):
    return detail(db, ident)

def public_ids(db):
    return set(db.scalars(select(Job.id).where(*repo.visible())))

def vector_record(db, ident):
    j = repo.get_job(db, ident)
    return output(db, j) if j and is_public(j) else None

def mark_synced(db, ident, digest):
    j = repo.get_job(db,ident)
    if j:
        j.content_hash = digest
        j.vector_synced_at = now()

def ensure_owner(db, actor, job_id):
    j = require(repo.get_job(db,job_id))
    companies.ensure_member(db,actor,j.company_id)
    return output(db,j)

def mine(db, actor):
    return [output(db,j) for j in repo.by_company(db,companies.memberships(db,actor["id"]))]

def moderation_queue(db, actor):
    if actor["role"] not in {"admin","staff"}:
        raise HTTPException(403, "Chỉ nhân sự kiểm duyệt")
    return [output(db,j) for j in repo.queue(db)]

def upsert(db, actor, data, ident=None):
    from app.ai.vector.sync import enqueue
    companies.ensure_member(db,actor,data.company_id)
    if data.deadline and data.deadline<today():
        raise HTTPException(422,"Hạn nộp phải từ hôm nay")
    if ident:
        ensure_owner(db,actor,ident)
        j=require(repo.get_job(db,ident))
        if j.deleted_at is not None:
            raise HTTPException(409, "Tin đã xóa")
        if j.company_id!=data.company_id:
            raise HTTPException(422, "Không đổi công ty sở hữu")
    else:
        j=Job(company_id=data.company_id)
        db.add(j)
    for key,value in data.model_dump(exclude={"benefits"}).items():
        setattr(j,key,value)
    j.details={**(j.details or {}),"benefits":data.benefits}
    j.moderation_status="pending"
    j.status="open"
    j.flags=assess(j,actor["id"])
    db.flush()
    enqueue(db,"jobs",j.id)
    db.commit()
    return output(db,j)

def review(db, actor, ident, data):
    from app.ai.vector.sync import enqueue
    if actor["role"] not in {"staff","admin"}:
        raise HTTPException(403,"Chỉ nhân sự kiểm duyệt")
    j=require(repo.get_job(db,ident))
    if j.moderation_status!="pending" or j.deleted_at or j.status!="open":
        raise HTTPException(409,"Tin không còn trong hàng chờ")
    if data.decision=="approved" and j.deadline and j.deadline<today():
        raise HTTPException(422,"Tin đã hết hạn")
    if data.decision=="rejected" and not data.reason.strip():
        raise HTTPException(422,"Nhập lý do từ chối")
    j.moderation_status=data.decision
    db.add(Review(job_id=j.id,reviewer_id=actor["id"],decision=data.decision,reason=data.reason))
    enqueue(db,"jobs",j.id)
    db.commit()
    return output(db,j)

def close(db,actor,ident,delete=False):
    from app.ai.vector.sync import enqueue
    ensure_owner(db,actor,ident)
    j=require(repo.get_job(db,ident))
    j.status="closed"
    if delete:
        j.deleted_at=now()
    enqueue(db,"jobs",j.id)
    db.commit()
    return {"ok":True}

def save(db,actor,ident,value):
    public_detail(db,ident)
    keys=dict(job_id=ident,user_id=actor["id"])
    old=first(db,SavedJob,**keys)
    if value and old is None:
        put(db,SavedJob,keys)
    elif old and not value:
        db.delete(old)
    db.commit()
    return {"saved":value}

def saved(db,actor):
    stmt=select(Job).join(SavedJob,Job.id==SavedJob.job_id).where(SavedJob.user_id==actor["id"],*repo.visible())
    return [output(db,j) for j in db.scalars(stmt)]

def public_by_code(db,code):
    job=first(db,Job,code=code,moderation_status="approved",deleted_at=None)
    if not job:
        return None,"unavailable"
    if job.deadline and job.deadline<today():
        return None,"expired"
    if not is_public(job):
        return None,"closed"
    return output(db,job),"active"
