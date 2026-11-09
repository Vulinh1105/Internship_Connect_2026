from sqlalchemy import case, func, or_, select, text
from app.core.config import today
from app.modules.applications.models import Application
from app.modules.students.models import Student
from .models import Job, Review, SavedJob

def get_job(db, ident):
    return db.get(Job, ident)

def visible():
    return (Job.status == "open", Job.moderation_status == "approved",
            Job.deleted_at.is_(None), or_(Job.deadline.is_(None), Job.deadline >= today()))

def hiring_company_ids(db, limit):
    count = func.count(Job.id)
    stmt = (select(Job.company_id).where(*visible()).group_by(Job.company_id)
            .order_by(count.desc(), Job.company_id).limit(limit))
    return list(db.scalars(stmt))

def find(db, q="", location="", category="", work_mode="", level="", salary_min=None, salary_max=None, offset=0, limit=20, company_id=None):
    stmt = select(Job).where(*visible())
    if company_id is not None:
        stmt = stmt.where(Job.company_id == company_id)
    for col, value in [(Job.location,location),(Job.category,category),(Job.work_mode,work_mode),(Job.level,level)]:
        if value:
            stmt = stmt.where(col.icontains(value, autoescape=True))
    if salary_min is not None:
        stmt = stmt.where(Job.salary_max >= salary_min)
    if salary_max is not None:
        stmt = stmt.where(Job.salary_min <= salary_max)
    if q.strip():
        if db.bind.dialect.name == "mysql":
            expr = text("MATCH(title, description, requirements) AGAINST (:term IN NATURAL LANGUAGE MODE)").bindparams(term=q.strip())
            stmt = stmt.where(expr)
            stmt = stmt.order_by(expr.desc() if hasattr(expr, "desc") else text("MATCH(title, description, requirements) AGAINST (:term IN NATURAL LANGUAGE MODE) DESC").bindparams(term=q.strip()))
        else:
            words = q.split()[:8]
            stmt = stmt.where(or_(*(col.icontains(word, autoescape=True)
                                  for word in words for col in (Job.title, Job.description, Job.requirements))))
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    return list(db.scalars(stmt.order_by(Job.id.desc()).offset(offset).limit(limit))), total

def by_company(db, company_ids):
    return list(db.scalars(select(Job).where(Job.company_id.in_(company_ids), Job.deleted_at.is_(None)).order_by(Job.id.desc())))

# Tin đã đóng không nằm trong hàng chờ: chỉ duyệt lại khi doanh nghiệp mở lại tin.
def queue(db):
    return list(db.scalars(select(Job).where(Job.moderation_status=="pending", Job.status=="open", Job.deleted_at.is_(None)).order_by(Job.id)))

def queue_count(db):
    return db.scalar(select(func.count()).select_from(Job).where(Job.moderation_status=="pending", Job.status=="open", Job.deleted_at.is_(None))) or 0

def approved_before(db, job_id):
    return db.scalar(select(func.count()).select_from(Review).where(Review.job_id==job_id, Review.decision=="approved")) or 0

def application_counts(db, job_ids):
    # {job_id: (tổng số đơn, số đơn đang chờ xử lý)}
    if not job_ids:
        return {}
    waiting = func.sum(case((Application.status == "pending", 1), else_=0))
    stmt = (select(Application.job_id, func.count(Application.id), waiting)
            .where(Application.job_id.in_(job_ids)).group_by(Application.job_id))
    return {job_id: (total, int(new or 0)) for job_id, total, new in db.execute(stmt)}

def latest_reviews(db, job_ids):
    # {job_id: lần kiểm duyệt gần nhất}
    if not job_ids:
        return {}
    latest = {}
    for review in db.scalars(select(Review).where(Review.job_id.in_(job_ids)).order_by(Review.id.desc())):
        latest.setdefault(review.job_id, review)
    return latest

def count_applications(db, job_id, statuses):
    return db.scalar(select(func.count()).select_from(Application)
                     .where(Application.job_id == job_id, Application.status.in_(statuses))) or 0

def applicant_user_ids(db, job_id, statuses):
    stmt = (select(Student.user_id).join(Application, Application.student_id == Student.id)
            .where(Application.job_id == job_id, Application.status.in_(statuses)))
    return list(db.scalars(stmt))
