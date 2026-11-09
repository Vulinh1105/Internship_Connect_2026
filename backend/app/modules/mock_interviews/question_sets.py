from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select

from app.common.records import record, require
from app.core.deps import allow
from app.modules.companies.models import Company, Member
from app.modules.companies.recruitment import manager
from app.modules.jobs.models import Job
from app.modules.jobs.repository import visible
from .models import QuestionSet

QUESTION_SECONDS = 600


def practice_job():
    fixture = Job.details["fixture_case"].as_string()
    return and_(or_(fixture.is_(None),fixture.in_(["","baseline_public"])),~Job.title.ilike("tin demo%"))


def joined_sets():
    return (select(QuestionSet,Job,Company).outerjoin(Job,QuestionSet.job_id==Job.id)
            .join(Company,Company.id==func.coalesce(QuestionSet.company_id,Job.company_id))
            .where(or_(QuestionSet.job_id.is_(None),practice_job())))


def public_rows(db, ident=None):
    stmt = joined_sets().where(QuestionSet.published.is_(True),or_(QuestionSet.job_id.is_(None),and_(*visible())))
    if ident is not None:
        stmt = stmt.where(QuestionSet.id==ident)
    return db.execute(stmt.order_by(Company.name,func.coalesce(Job.title,QuestionSet.position_title),QuestionSet.title,QuestionSet.id))


def output(row,job,company):
    return {**record(row),"company_id":company.id,"company_name":company.name,
            "job_title":job.title if job else row.position_title}


def catalog(db,actor):
    allow(actor,"student")
    return [{**record(row,"id","job_id","title","description"),
             "job_title":job.title if job else row.position_title,"job_category":job.category if job else None,
             "company_id":company.id,"company_name":company.name,"question_count":len(row.questions),
             "difficulties":list(dict.fromkeys(q["difficulty"] for q in row.questions)),
             "estimated_seconds":len(row.questions)*QUESTION_SECONDS}
            for row,job,company in public_rows(db)]


def mine(db,actor):
    allow(actor,"company_member")
    companies = select(Member.company_id).where(Member.user_id==actor["id"],Member.active.is_(True),Member.manager.is_(True))
    stmt = joined_sets().where(Company.id.in_(companies)).order_by(QuestionSet.id.desc())
    return [output(row,job,company) for row,job,company in db.execute(stmt)]


def target(db,actor,job_id=None,company_id=None,position_title=None):
    if job_id is not None:
        job = require(db.scalar(select(Job).where(Job.id==job_id,practice_job())),"Không tìm thấy vị trí tuyển dụng")
        manager(db,actor,job.company_id)
        if company_id is not None and company_id!=job.company_id:
            raise HTTPException(422,"Vị trí tuyển dụng không thuộc doanh nghiệp đã chọn")
        return job,require(db.get(Company,job.company_id))
    if company_id is None or not position_title or not 2<=len(position_title.strip())<=200:
        raise HTTPException(422,"Chọn doanh nghiệp và nhập tên vị trí từ 2 đến 200 ký tự.")
    manager(db,actor,company_id)
    return None,require(db.get(Company,company_id))


def save(db,actor,data,ident=None):
    if ident is None:
        job,company = target(db,actor,data.job_id,data.company_id,data.position_title)
        row = QuestionSet(job_id=job.id if job else None,company_id=None if job else company.id,
                          position_title=None if job else data.position_title)
    else:
        row = require(db.get(QuestionSet,ident))
        job,company = target(db,actor,row.job_id,row.company_id,row.position_title)
        if data.job_id!=row.job_id or (data.company_id is not None and data.company_id!=company.id):
            raise HTTPException(422,"Bộ câu hỏi đã tạo phải giữ nguyên doanh nghiệp và tin tuyển dụng")
        if job is None:
            row.position_title=data.position_title
    if job and job.deleted_at is not None and data.published:
        raise HTTPException(422,"Tin đã gỡ chỉ có thể lưu bộ câu hỏi ở trạng thái nháp")
    row.title,row.description,row.published = data.title,data.description.strip(),data.published
    row.questions = [q.model_dump() for q in data.questions]
    db.add(row)
    db.commit()
    return output(row,job,company)


def remove(db,actor,ident):
    row = require(db.get(QuestionSet,ident))
    target(db,actor,row.job_id,row.company_id,row.position_title)
    db.delete(row)
    db.commit()
    return {"ok":True}


def snapshot(db,ident):
    found = public_rows(db,ident).first()
    if not found:
        raise HTTPException(404,"Bộ câu hỏi chưa công khai hoặc vị trí đã ngừng tuyển")
    row,job,company = found
    title=job.title if job else row.position_title
    source={"id":row.id,"title":row.title,"company_name":company.name,"job_title":title}
    plan=[]
    for q in row.questions:
        domains=["knowledge","problem_solving"] if q["kind"]=="both" else [q["kind"]]
        plan.append({"question":q["question"],"kind":q["kind"],"domains":domains,"seconds":QUESTION_SECONDS,
                     "level":job.level if job else "intern","difficulty":q["difficulty"],"source":source,
                     "topic_criteria":[value for value in (q["criteria"],q["guidance"]) if value]})
    return row.job_id,title[:100],plan
