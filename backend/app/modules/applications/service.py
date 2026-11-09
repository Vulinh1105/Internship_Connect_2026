from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.common.records import record,require
from app.core.config import now
from app.modules.students import service as students
from app.modules.jobs import service as jobs
from app.modules.companies import service as companies
from app.modules.companies.models import PlacementFeedback
from app.modules.notifications import service as notifications
from .models import Application,ApplicationEvent
from . import repository as repo

def event(db,a,actor_id,status):
    db.add(ApplicationEvent(application_id=a.id,actor_id=actor_id,before=a.status,after=status))
    a.status=status

def applied_ids(db,student_id):
    # Đơn đã rút coi như chưa ứng tuyển: tin vẫn được gợi ý và nộp lại được.
    return set(db.scalars(select(Application.job_id).where(Application.student_id==student_id,Application.status!="withdrawn")))

def show(db,a,actor=None):
    try:
        job=jobs.detail(db,a.job_id,actor)
        title=job["title"]
    except HTTPException:
        title="Tin đã đóng hoặc không còn công khai"
    result = {**record(a),"job_title":title}
    feedback = db.get(PlacementFeedback,a.id)
    if feedback:
        result.update(record(feedback,"completed_at","review_status"))
        if actor and actor["role"]=="company_member":
            result.update(record(feedback,"interviewer_rating","interviewer_note"))
    return result

def apply(db,actor,data):
    from app.ai.matching.service import score_application
    s=students.get_own(db,actor)
    job=jobs.public_detail(db,data.job_id)
    if data.cv_id:
        students.own_cv(db,actor,data.cv_id)
    if data.job_id in applied_ids(db,s.id):
        raise HTTPException(409,"Bạn đã ứng tuyển tin này")
    match=score_application(db,actor,s.id,job,data.cv_id)
    # Mỗi sinh viên chỉ có một đơn cho mỗi tin (ràng buộc duy nhất), nên nộp lại sau khi rút là mở lại đơn cũ.
    a=db.scalar(select(Application).where(Application.student_id==s.id,Application.job_id==data.job_id))
    reapply=a is not None
    if reapply:
        event(db,a,actor["id"],"pending")
        a.cv_id,a.cover_letter,a.match_score,a.match_reason=data.cv_id,data.cover_letter,match["match_score"],match
        a.submitted_at,a.decision_at,a.decision_reason=now(),None,None
    else:
        a=Application(student_id=s.id,job_id=data.job_id,cv_id=data.cv_id,cover_letter=data.cover_letter,
                      status="pending",match_score=match["match_score"],match_reason=match)
        db.add(a)
    try:
        db.flush()
        if not reapply:
            db.add(ApplicationEvent(application_id=a.id,actor_id=actor["id"],after="pending"))
        score=a.match_score
        fit=f" (phù hợp {round(score)}%)" if score is not None else ""
        notifications.send_many(db,companies.member_user_ids(db,job["company_id"]),"application_new",
            f"{s.name} ứng tuyển {job['title']}{fit}.",job["id"])
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
    # Doanh nghiệp xem được tên, ngành học và kỹ năng trong hồ sơ đã nộp của sinh viên.
    result = []
    for a in db.scalars(select(Application).filter_by(job_id=job_id)
                        .order_by(Application.match_score.desc(),Application.id)):
        profile = students.applicant_view(db,a.student_id,a.cv_id)
        row = {**show(db,a,actor),"student_name":students.public_name(db,a.student_id),**profile}
        if not profile["skills"]:
            row.pop("match_reason",None)
        result.append(row)
    return result

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
    info=jobs.brief(db,a.job_id)
    return {"application_id":a.id,"user_id":students.user_id_for(db,a.student_id),"status":a.status,
            "student_name":students.public_name(db,a.student_id),
            "job_id":info["id"],"job_title":info["title"],"company_name":info["company_name"]}

def reviewing(db,actor,ident):
    a=authorized(db,actor,ident)
    if a.status=="pending":
        event(db,a,actor["id"],"reviewing")

def decision(db,actor,ident,status,reason=""):
    from app.modules.interviews import service as interviews
    a=authorized(db,actor,ident)
    if a.status not in {"pending","reviewing"}:
        raise HTTPException(409,"Đơn đã kết thúc xét duyệt")
    if (actor["role"]=="student") != (status=="withdrawn"):
        raise HTTPException(403,"Không được thực hiện thay đổi này")
    reason=reason.strip()
    if status=="rejected" and not reason:
        raise HTTPException(422,"Nhập lý do từ chối")
    if a.status==status:
        return show(db,a,actor)
    event(db,a,actor["id"],status)
    if status=="rejected":
        a.decision_reason=reason
    if status in {"accepted","rejected","withdrawn"}:
        a.decision_at=now()
    if status in {"rejected","withdrawn"}:
        interviews.cancel_for_application(db,a.id)
    notify_decision(db,a,status)
    db.commit()
    return show(db,a,actor)

STATUS_TEXT={"reviewing":"đang được xét","accepted":"đã được nhận","rejected":"đã bị từ chối"}

def notify_decision(db,a,status):
    info=jobs.brief(db,a.job_id)
    if status=="withdrawn":
        # Sinh viên tự rút đơn: báo cho doanh nghiệp, không báo lại cho chính sinh viên.
        notifications.send_many(db,companies.member_user_ids(db,info["company_id"]),"application_withdrawn",
            f"{students.public_name(db,a.student_id)} đã rút đơn {info['title']}.",info["id"])
        return
    text=f"Đơn ứng tuyển {info['title']} tại {info['company_name']} {STATUS_TEXT[status]}."
    if status=="accepted":
        text+=" Hãy theo dõi lịch phỏng vấn hoặc liên hệ từ doanh nghiệp."
    if status=="rejected" and a.decision_reason:
        text+=f" Lý do: {a.decision_reason}"
    notifications.send(db,students.user_id_for(db,a.student_id),"application_status",text,a.id)

def download(db,actor,ident):
    a=authorized(db,actor,ident)
    if a.cv_id is None:
        raise HTTPException(404,"Đơn chưa đính kèm CV")
    return students.file_for_student(db,a.student_id,a.cv_id,submitted=True)
