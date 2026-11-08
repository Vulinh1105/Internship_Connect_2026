from sqlalchemy import select
from fastapi import HTTPException
from app.core.config import now,LOCAL_TZ
from app.common.records import record,require
from app.modules.applications import service as applications
from app.modules.notifications import service as notifications
from .models import Interview
from . import repository as repo

def when(t):
    return f"{t:%H:%M} ngày {t:%d/%m}"

REPLY_TEXT={"confirmed":"đã xác nhận lịch phỏng vấn","declined":"đã từ chối lịch phỏng vấn",
            "reschedule_requested":"xin đổi lịch phỏng vấn"}

def invite(db,actor,data):
    if actor["role"]!="company_member":
        raise HTTPException(403,"Chỉ doanh nghiệp được mời")
    ctx=applications.interview_context(db,actor,data.application_id)
    if ctx["status"] in {"rejected","withdrawn"}:
        raise HTTPException(409,"Đơn đã bị từ chối hoặc rút")
    time=data.scheduled_at
    if time.tzinfo:
        time=time.astimezone(LOCAL_TZ).replace(tzinfo=None)
    if time<=now():
        raise HTTPException(422,"Thời gian phỏng vấn phải ở tương lai")
    active=db.scalar(select(Interview).where(Interview.application_id==data.application_id,
                Interview.status.in_(["invited","confirmed"])))
    if active:
        raise HTTPException(409,"Đơn đã có lịch đang hiệu lực")
    cancel_for_application(db,data.application_id)
    row=Interview(application_id=data.application_id,invited_by=actor["id"],scheduled_at=time,
                  location=data.location,note=data.note,status="invited")
    db.add(row)
    applications.reviewing(db,actor,data.application_id)
    db.flush()
    notifications.send(db,ctx["user_id"],"interview",
        f"{ctx['company_name']} mời bạn phỏng vấn vị trí {ctx['job_title']} lúc {when(time)}. Hãy xác nhận hoặc xin đổi lịch.",row.id)
    db.commit()
    return record(row)

def mine(db,actor):
    if actor["role"] not in {"student","company_member"}:
        return []
    result=[]
    for row in db.scalars(select(Interview).order_by(Interview.scheduled_at)):
        try:
            ctx=applications.interview_context(db,actor,row.application_id)
        except HTTPException as e:
            if e.status_code in (403,404):
                continue
            raise
        result.append({**record(row),"student_name":ctx["student_name"]})
    return result

def reply(db,actor,ident,data):
    if actor["role"]!="student":
        raise HTTPException(403,"Chỉ sinh viên được phản hồi lời mời")
    i=require(repo.get_interview(db,ident))
    ctx=applications.interview_context(db,actor,i.application_id)
    if i.status!="invited" or i.scheduled_at<=now():
        raise HTTPException(409,"Lời mời đã phản hồi hoặc hết hiệu lực")
    if data.action=="reschedule_requested" and not data.message.strip():
        raise HTTPException(422,"Nhập thời gian đề xuất")
    i.status=data.action
    i.response=data.message
    text=f"{ctx['student_name']} {REPLY_TEXT[i.status]} {ctx['job_title']} ({when(i.scheduled_at)})"
    text+=f": {data.message.strip()}" if data.message.strip() else "."
    notifications.send(db,i.invited_by,"interview_reply",text,i.id)
    db.commit()
    return record(i)

def cancel_for_application(db,ident):
    for i in db.scalars(select(Interview).where(Interview.application_id==ident,
               Interview.status.in_(["invited","confirmed","reschedule_requested"]))):
        i.status="cancelled"
        i.cancelled_at=now()

def cancel(db,actor,ident):
    if actor["role"]!="company_member":
        raise HTTPException(403,"Chỉ doanh nghiệp được hủy")
    i=require(repo.get_interview(db,ident))
    ctx=applications.interview_context(db,actor,i.application_id)
    i.status="cancelled";i.cancelled_at=now()
    notifications.send(db,ctx["user_id"],"interview_cancelled",
        f"{ctx['company_name']} đã hủy lịch phỏng vấn {ctx['job_title']} ngày {i.scheduled_at:%d/%m}.",i.id)
    db.commit()
    return record(i)
