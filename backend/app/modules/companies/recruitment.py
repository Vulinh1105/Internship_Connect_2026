from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import distinct, func, select, update
from sqlalchemy.exc import IntegrityError

from app.common.records import first, record, require
from app.core.config import now
from app.core.deps import Actor, DB, allow
from app.core.rate_limit import enforce
from app.modules.applications.models import Application
from app.modules.applications.service import authorized
from app.modules.auth.models import AccountSettings, User
from app.modules.interviews.models import Interview
from app.modules.jobs.models import Job, JobMetrics, JobReport
from app.modules.jobs.service import public_detail
from app.modules.students.models import Student
from . import service as companies
from .models import Company, Member, PlacementFeedback

router = APIRouter(prefix="/api", tags=["recruitment"])


class Rating(BaseModel):
    rating: int = Field(ge=1,le=5)
    note: str = Field(min_length=1,max_length=2000,pattern=r"\S")


class ReportInput(BaseModel):
    reason: str = Field(min_length=10,max_length=2000,pattern=r"\S")


class ReportDecision(BaseModel):
    status: Literal["resolved","dismissed"]
    note: str = Field(min_length=1,max_length=2000,pattern=r"\S")


class ReviewDecision(BaseModel):
    status: Literal["approved","rejected"]


@router.post("/jobs/{job_id}/views")
def count_view(job_id: int, db: DB, request: Request):
    enforce(("job-view",request.client.host if request.client else "local",job_id),60,60)
    public_detail(db,job_id)
    stmt = update(JobMetrics).where(JobMetrics.job_id==job_id).values(views=JobMetrics.views+1)
    if not db.execute(stmt).rowcount:
        try:
            with db.begin_nested():
                db.add(JobMetrics(job_id=job_id,views=1))
                db.flush()
        except IntegrityError:
            db.execute(stmt)
    db.commit()
    return {"ok":True}


@router.get("/recruitment/stats")
def stats(db: DB, actor: Actor):
    allow(actor,"company_member")
    scope = companies.memberships(db,actor["id"])
    stmt = select(Job.id,Job.title,func.coalesce(JobMetrics.views,0)).outerjoin(JobMetrics).where(Job.company_id.in_(scope))
    rows = {ident:{"id":ident,"title":title,"views":views,"total":0,"pending":0,"invited":0,"accepted":0}
            for ident,title,views in db.execute(stmt.order_by(Job.id.desc()))}
    counts = select(Application.job_id,Application.status,func.count()).where(Application.job_id.in_(rows)).group_by(
        Application.job_id,Application.status)
    for job_id,status,count in db.execute(counts):
        rows[job_id]["total"] += count
        if status in ("pending","reviewing"):
            rows[job_id]["pending"] += count
        if status=="accepted":
            rows[job_id]["accepted"] += count
    invited = (select(Application.job_id,func.count(distinct(Application.id))).join(Interview)
               .where(Application.job_id.in_(rows)).group_by(Application.job_id))
    for job_id,count in db.execute(invited):
        rows[job_id]["invited"] = count
    return [{**row,"conversion":round(100*row["total"]/row["views"],1) if row["views"] else None}
            for row in rows.values()]


def manager(db, actor, company_id):
    companies.ensure_member(db,actor,company_id)
    if not first(db,Member,company_id=company_id,user_id=actor["id"],active=True,manager=True):
        raise HTTPException(403,"Chỉ người quản lý doanh nghiệp được thực hiện thao tác này")


@router.get("/companies/{company_id}/members")
def members(company_id: int, db: DB, actor: Actor):
    manager(db,actor,company_id)
    stmt = select(Member,User.email).join(User).where(Member.company_id==company_id).order_by(Member.id)
    return [{**record(row,"id","active","manager"),"email":email} for row,email in db.execute(stmt)]


@router.delete("/companies/{company_id}/members/{member_id}")
def revoke(company_id: int, member_id: int, db: DB, actor: Actor):
    manager(db,actor,company_id)
    row = require(first(db,Member,id=member_id,company_id=company_id))
    if row.manager:
        raise HTTPException(409,"Không thể thu hồi tài khoản quản lý tại đây")
    row.active = False
    db.commit()
    return {"ok":True}


def lock_feedback(db, application_id):
    db.scalar(select(Application.id).where(Application.id==application_id).with_for_update())
    row = db.get(PlacementFeedback,application_id)
    if row is None:
        row = PlacementFeedback(application_id=application_id)
        db.add(row)
    return row


@router.post("/applications/{ident}/internship-completed")
def complete(ident: int, db: DB, actor: Actor):
    allow(actor,"company_member")
    app = authorized(db,actor,ident)
    if app.status!="accepted":
        raise HTTPException(409,"Chỉ xác nhận hoàn thành cho ứng viên đã được nhận")
    row = lock_feedback(db,ident)
    row.completed_at = row.completed_at or now()
    db.commit()
    return {"ok":True}


@router.put("/applications/{ident}/interview-feedback")
def interview_feedback(ident: int, data: Rating, db: DB, actor: Actor):
    allow(actor,"company_member")
    authorized(db,actor,ident)
    interview = db.scalar(select(Interview.id).where(Interview.application_id==ident,
                          Interview.status=="confirmed",Interview.scheduled_at<=now()).limit(1))
    if interview is None:
        raise HTTPException(409,"Cần có lịch phỏng vấn đã xác nhận và đã tới giờ")
    row = lock_feedback(db,ident)
    row.interviewer_rating,row.interviewer_note = data.rating,data.note.strip()
    db.commit()
    return {"ok":True}


@router.post("/applications/{ident}/company-review")
def company_review(ident: int, data: Rating, db: DB, actor: Actor):
    allow(actor,"student")
    app = authorized(db,actor,ident)
    row = lock_feedback(db,ident)
    if app.status!="accepted" or not row.completed_at:
        raise HTTPException(409,"Doanh nghiệp cần xác nhận đã hoàn thành kỳ thực tập")
    if row.review_status is not None:
        raise HTTPException(409,"Bạn đã gửi đánh giá cho kỳ thực tập này")
    row.student_rating,row.student_review,row.review_status = data.rating,data.note.strip(),"pending"
    db.commit()
    return {"ok":True}


@router.get("/companies/{company_id}/reviews")
def public_reviews(company_id: int, db: DB):
    stmt = (select(PlacementFeedback).join(Application).join(Job)
            .where(Job.company_id==company_id,PlacementFeedback.review_status=="approved")
            .order_by(PlacementFeedback.completed_at.desc()).limit(100))
    return [record(row,"student_rating","student_review") for row in db.scalars(stmt)]


@router.post("/jobs/{job_id}/reports")
def report_job(job_id: int, data: ReportInput, db: DB, actor: Actor):
    public_detail(db,job_id)
    db.add(JobReport(job_id=job_id,reporter_id=actor["id"],reason=data.reason.strip()))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,"Bạn đã báo cáo tin này")
    return {"ok":True}


@router.get("/admin/overview")
def overview(db: DB, actor: Actor):
    allow(actor,"admin")
    reviews = (select(PlacementFeedback,Company.name).join(Application).join(Job).join(Company)
               .where(PlacementFeedback.review_status.in_(("pending","approved")))
               .order_by(PlacementFeedback.review_status.desc(),PlacementFeedback.application_id.desc()).limit(100))
    reports = select(JobReport,Job.title).join(Job).where(JobReport.status=="pending").order_by(JobReport.id).limit(100)
    counts = {name:db.scalar(select(func.count()).select_from(model)) for name,model in
              (("users",User),("companies",Company),("jobs",Job),("applications",Application))}
    requests = select(AccountSettings,User.email).join(User)
    return {"counts":counts,
            "reviews":[{**record(row,"application_id","student_rating","student_review","review_status"),"company":name}
                       for row,name in db.execute(reviews)],
            "reports":[{**record(row),"title":title} for row,title in db.execute(reports)],
            "closure_requests":[{"id":row.user_id,"email":email,"action":row.options["closure_request"]}
                                for row,email in db.execute(requests) if row.options.get("closure_request")]}


@router.patch("/admin/job-reports/{ident}")
def resolve_report(ident: int, data: ReportDecision, db: DB, actor: Actor):
    allow(actor,"admin")
    require(db.get(JobReport,ident))
    result = db.execute(update(JobReport).where(JobReport.id==ident,JobReport.status=="pending")
                        .values(status=data.status,resolution=data.note.strip()))
    if not result.rowcount:
        raise HTTPException(409,"Báo cáo đã được xử lý")
    db.commit()
    return {"ok":True}


@router.patch("/admin/company-reviews/{ident}")
def moderate_review(ident: int, data: ReviewDecision, db: DB, actor: Actor):
    allow(actor,"admin")
    require(db.get(PlacementFeedback,ident))
    allowed = ("pending",) if data.status=="approved" else ("pending","approved")
    changed = db.execute(update(PlacementFeedback).where(PlacementFeedback.application_id==ident,
                         PlacementFeedback.review_status.in_(allowed)).values(review_status=data.status))
    if not changed.rowcount:
        raise HTTPException(409,"Đánh giá không còn ở trạng thái có thể xử lý")
    db.commit()
    return {"ok":True}


@router.post("/admin/account-closures/{ident}")
def disable_account(ident: int, db: DB, actor: Actor):
    allow(actor,"admin")
    if ident==actor["id"]:
        raise HTTPException(409,"Không thể vô hiệu hóa tài khoản đang xử lý yêu cầu")
    settings = require(db.get(AccountSettings,ident))
    request = settings.options.get("closure_request")
    if not request:
        raise HTTPException(409,"Tài khoản không có yêu cầu đang chờ")
    user = require(db.get(User,ident))
    if not user.active:
        raise HTTPException(409,"Tài khoản đã bị vô hiệu hóa")
    user.active = False
    user.session_version += 1
    if request=="disable":
        settings.options = {key:value for key,value in settings.options.items() if key!="closure_request"}
    db.commit()
    return {"ok":True}
