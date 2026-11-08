from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.common.records import record,require
from app.core.config import now
from app.modules.students import service as students
from app.modules.jobs import service as jobs
from app.modules.notifications import service as notifications
from .models import Application,ApplicationEvent
from . import repository as repo

def event(db,a,actor_id,status):
    db.add(ApplicationEvent(application_id=a.id,actor_id=actor_id,before=a.status,after=status))
    a.status=status

def applied_ids(db,student_id):
    return set(db.scalars(select(Application.job_id).filter_by(student_id=student_id)))

def show(db,a,actor=None):
    try:
        job=jobs.detail(db,a.job_id,actor)
        title=job["title"]
    except HTTPException:
        title="Tin đã đóng hoặc không còn công khai"
    return {**record(a),"job_title":title}

def apply(db,actor,data):
    from app.ai.matching.service import score_application
    s=students.get_own(db,actor)
    job=jobs.public_detail(db,data.job_id)
    if data.cv_id:
        students.own_cv(db,actor,data.cv_id)
    if data.job_id in applied_ids(db,s.id):
        raise HTTPException(409,"Bạn đã ứng tuyển tin này")
    match=score_application(db,actor,s.id,job,data.cv_id)
    a=Application(student_id=s.id,job_id=data.job_id,cv_id=data.cv_id,cover_letter=data.cover_letter,
                  status="pending",match_score=match["match_score"],match_reason=match)
    db.add(a)
    try:
        db.flush()
        db.add(ApplicationEvent(application_id=a.id,actor_id=actor["id"],after="pending"))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,"Bạn đã ứng tuyển tin này")
    return show(db,a,actor)

def mine(db,actor):
    s=students.get_own(db,actor)
    return [show(db,a,actor) for a in db.scalars(select(Application).filter_by(student_id=s.id).order_by(Application.id.desc()))]

def for_job(db,actor,job_id):
    jobs.ensure_owner(db,actor,job_id)
    return [{**show(db,a,actor),"student_name":students.public_name(db,a.student_id)}
            for a in db.scalars(select(Application).filter_by(job_id=job_id)
                              .order_by(Application.match_score.desc(),Application.id))]

def authorized(db,actor,ident):
    a=require(repo.get_application(db,ident),"Không tìm thấy đơn")
    if actor["role"]=="student":
        if students.get_own(db,actor).id!=a.student_id:
            raise HTTPException(403,"Đơn không thuộc tài khoản này")
    else:
        jobs.ensure_owner(db,actor,a.job_id)
    return a

def interview_context(db,actor,ident):
    a=authorized(db,actor,ident)
    return {"application_id":a.id,"user_id":students.user_id_for(db,a.student_id),"status":a.status,
            "student_name":students.public_name(db,a.student_id)}

def reviewing(db,actor,ident):
    a=authorized(db,actor,ident)
    if a.status=="pending":
        event(db,a,actor["id"],"reviewing")

def decision(db,actor,ident,status):
    from app.modules.interviews import service as interviews
    a=authorized(db,actor,ident)
    if a.status not in {"pending","reviewing"}:
        raise HTTPException(409,"Đơn đã kết thúc xét duyệt")
    if (actor["role"]=="student") != (status=="withdrawn"):
        raise HTTPException(403,"Không được thực hiện thay đổi này")
    if a.status==status:
        return show(db,a,actor)
    event(db,a,actor["id"],status)
    if status in {"accepted","rejected","withdrawn"}:
        a.decision_at=now()
    if status in {"rejected","withdrawn"}:
        interviews.cancel_for_application(db,a.id)
    notifications.send(db,students.user_id_for(db,a.student_id),"application_status",f"Đơn #{a.id} cập nhật: {status}",a.id)
    db.commit()
    return show(db,a,actor)

def download(db,actor,ident):
    a=authorized(db,actor,ident)
    if a.cv_id is None:
        raise HTTPException(404,"Đơn chưa đính kèm CV")
    return students.file_for_student(db,a.student_id,a.cv_id,submitted=True)
