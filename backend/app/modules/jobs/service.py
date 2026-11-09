from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import now, today
from app.common.pagination import page
from app.common.records import first, put, record, require
from app.modules.companies import service as companies
from app.modules.notifications import service as notifications
from . import repository as repo
from .models import Job, Review, SavedJob
from .moderation import assess

# Các trường mô tả thêm của tin, lưu trong cột details cùng với quyền lợi.
DETAIL_FIELDS=("experience","education","quantity","working_hours","employment_schedule","address")

# Sửa các trường này trên tin đã duyệt thì phải kiểm duyệt lại: mọi trường chữ tự do (người duyệt cần đọc) và mức lương.
# Chỉ các trường dạng lựa chọn hoặc con số (hạn nộp, số lượng, học vấn, hình thức, cấp độ, lịch làm việc) có hiệu lực ngay.
MATERIAL_FIELDS=("title","description","requirements","category","location","salary_min","salary_max")
MATERIAL_DETAILS=("benefits","address","experience","working_hours")
# Đơn còn đang chờ doanh nghiệp xử lý.
ACTIVE_APPLICATIONS=("pending","reviewing")

def material(j):
    details=j.details or {}
    return (tuple(getattr(j,key) for key in MATERIAL_FIELDS),tuple(sorted(str(s).strip() for s in (j.skills or []))),
            tuple(details.get(key) or "" for key in MATERIAL_DETAILS))

def is_public(j):
    return (j.status == "open" and j.moderation_status == "approved" and j.deleted_at is None
            and (j.deadline is None or j.deadline >= today()))

def output(db, j):
    company = companies.detail(db, j.company_id)
    return {**record(j), "company_name": company["name"], "company_has_logo": company["has_logo"], "active": is_public(j)}

def search(db, **filters):
    rows, total = repo.find(db, **filters)
    return page([output(db,j) for j in rows],filters.get("offset",0),filters.get("limit",20),total)

def detail(db, ident, actor=None):
    j = require(repo.get_job(db, ident), "Không tìm thấy tin")
    if not is_public(j):
        if not actor or (actor["role"] not in {"staff","admin"} and j.company_id not in companies.memberships(db,actor["id"])):
            raise HTTPException(404, "Tin không công khai hoặc đã hết hạn")
    return output(db,j)

def brief(db, ident):
    # Dùng cho thông báo: cần tên tin và công ty kể cả khi tin đã đóng hoặc chưa công khai.
    j = require(repo.get_job(db, ident), "Không tìm thấy tin")
    return {"id": j.id, "title": j.title, "company_id": j.company_id,
            "company_name": companies.company_name(db, j.company_id)}

def public_detail(db, ident):
    return detail(db, ident)

def hiring_companies(db, limit=10):
    return [companies.company_name(db, ident) for ident in repo.hiring_company_ids(db, limit)]

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
    rows = repo.by_company(db, companies.memberships(db, actor["id"]))
    ids = [j.id for j in rows]
    counts = repo.application_counts(db, ids)
    reviews = repo.latest_reviews(db, ids)
    result = []
    for j in rows:
        total, waiting = counts.get(j.id, (0, 0))
        review = reviews.get(j.id)
        # Chỉ hiện lý do khi tin đang ở trạng thái bị từ chối (sửa và gửi lại thì lý do cũ không còn áp dụng).
        reason = review.reason.strip() if review and review.decision == "rejected" and j.moderation_status == "rejected" else ""
        result.append({**output(db, j), "application_count": total, "new_application_count": waiting,
                       "rejection_reason": reason or None})
    return result

def moderation_queue(db, actor):
    if actor["role"] not in {"admin","staff"}:
        raise HTTPException(403, "Chỉ nhân sự kiểm duyệt")
    rows = repo.queue(db)
    reviews = repo.latest_reviews(db, [j.id for j in rows])
    # last_review: lần kiểm duyệt trước (nếu có) để biết tin này là tin mới hay tin gửi lại.
    return [{**output(db, j), "last_review": ({"decision": reviews[j.id].decision, "reason": reviews[j.id].reason}
                                              if j.id in reviews else None)} for j in rows]

def moderation_count(db, actor):
    if actor["role"] not in {"admin","staff"}:
        raise HTTPException(403, "Chỉ nhân sự kiểm duyệt")
    return {"pending": repo.queue_count(db)}

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
        before=material(j)
    else:
        j=Job(company_id=data.company_id)
        db.add(j)
    for key,value in data.model_dump(exclude={"benefits",*DETAIL_FIELDS}).items():
        setattr(j,key,value)
    # Bỏ giá trị cũ rồi ghi giá trị mới để doanh nghiệp xóa trống được một trường.
    details={k:v for k,v in (j.details or {}).items() if k not in DETAIL_FIELDS}
    details.update({k:getattr(data,k) for k in DETAIL_FIELDS if getattr(data,k) not in (None,"")})
    j.details={**details,"benefits":data.benefits}
    if not ident or j.moderation_status!="approved" or material(j)!=before:
        j.moderation_status="pending"
    if not ident:
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
    first_approval=data.decision=="approved" and repo.approved_before(db,j.id)==0
    j.moderation_status=data.decision
    db.add(Review(job_id=j.id,reviewer_id=actor["id"],decision=data.decision,reason=data.reason))
    if data.decision=="approved":
        text=f"Tin {j.title} đã được duyệt và hiển thị công khai."
        kind="job_approved"
    else:
        text=f"Tin {j.title} bị từ chối. Lý do: {data.reason.strip()}. Hãy chỉnh sửa và gửi duyệt lại."
        kind="job_rejected"
    notifications.send_many(db,companies.member_user_ids(db,j.company_id),kind,text,j.id)
    if first_approval:
        # Chỉ báo người theo dõi lần đầu tin được duyệt; sửa tin rồi duyệt lại không báo thêm.
        notifications.send_many(db,companies.follower_user_ids(db,j.company_id),"company_new_job",
            f"{companies.company_name(db,j.company_id)} vừa đăng tin {j.title}.",j.id)
    enqueue(db,"jobs",j.id)
    db.commit()
    return output(db,j)

def close_job(db,j,notify_applicants=True):
    from app.ai.vector.sync import enqueue
    was_open=j.status!="closed"
    j.status="closed"
    enqueue(db,"jobs",j.id)
    if was_open and notify_applicants:
        notifications.send_many(db,repo.applicant_user_ids(db,j.id,ACTIVE_APPLICATIONS),"job_closed",
            f"Tin {j.title} đã đóng tuyển. Đơn của bạn chưa có kết quả; bạn có thể theo dõi trạng thái trong mục Đơn ứng tuyển.",j.id)

def close(db,actor,ident,delete=False):
    ensure_owner(db,actor,ident)
    j=require(repo.get_job(db,ident))
    if delete and repo.count_applications(db,j.id,ACTIVE_APPLICATIONS):
        raise HTTPException(409,"Tin còn đơn đang chờ xử lý. Hãy xử lý hết các đơn hoặc chỉ đóng tin.")
    close_job(db,j)
    if delete:
        j.deleted_at=now()
    db.commit()
    return {"ok":True}

def reopen(db,actor,ident):
    from app.ai.vector.sync import enqueue
    ensure_owner(db,actor,ident)
    j=require(repo.get_job(db,ident))
    if j.deleted_at is not None:
        raise HTTPException(409,"Tin đã xóa")
    if j.status!="closed":
        raise HTTPException(409,"Tin đang mở")
    if j.deadline and j.deadline<today():
        raise HTTPException(422,"Hạn nộp đã qua. Hãy sửa hạn nộp trước khi mở lại tin")
    j.status="open"
    enqueue(db,"jobs",j.id)
    db.commit()
    return output(db,j)

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
