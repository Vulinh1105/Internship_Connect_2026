from sqlalchemy import func, or_, select, text
from app.core.config import today
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

def find(db, q="", location="", category="", work_mode="", level="", salary_min=None, salary_max=None, offset=0, limit=20):
    stmt = select(Job).where(*visible())
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

def queue(db):
    return list(db.scalars(select(Job).where(Job.moderation_status=="pending", Job.deleted_at.is_(None)).order_by(Job.id)))
