from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import func, select, update
from app.ai.interview_engine import planner, report
from app.common.file_parsing import redact
from app.core.config import AI_BACKEND, DAILY_MOCKS, now
from app.core.deps import allow
from app.modules.jobs import service as jobs
from app.modules.students import service as students
from .models import Answer, MockSession, Question, Report
from .question_sets import QUESTION_SECONDS, snapshot
from .schemas import Submit

def roles(db):
    return list(db.scalars(select(Question.role).distinct().order_by(Question.role)))

def session(db,actor,ident):
    allow(actor,"student")
    item=db.scalar(select(MockSession).where(MockSession.id==ident,MockSession.user_id==actor["id"]))
    if not item:
        raise HTTPException(404,"Không tìm thấy buổi luyện")
    return item

def saved_report(db,ident):
    return db.scalar(select(Report.report).where(Report.session_id==ident))

def answers_for(db,ident):
    return list(db.scalars(select(Answer).where(Answer.session_id==ident).order_by(Answer.id)))

def expire(db,item):
    if item.state!="active" or item.expires_at>now():
        return
    db.execute(update(MockSession).where(MockSession.id==item.id,MockSession.state=="active",
        MockSession.expires_at<=now()).values(state="expired"))
    db.commit()
    db.refresh(item)


def finish(db,actor,ident):
    item=session(db,actor,ident)
    expire(db,item)
    db.execute(update(MockSession).where(MockSession.id==ident,MockSession.state=="active")
               .values(state="finished"))
    db.commit()
    db.refresh(item)
    return view(db,item)


def evaluate(db,actor,ident):
    item=session(db,actor,ident)
    expire(db,item)
    if saved_report(db,ident) is not None:
        return view(db,item)
    current=now()
    if item.state=="evaluating" and item.expires_at>current:
        raise HTTPException(409,"Buổi phỏng vấn đang được chấm. Hãy tải lại sau.")
    if item.state not in {"finished","expired","evaluating"}:
        raise HTTPException(409,"Hãy kết thúc buổi phỏng vấn trước khi chấm điểm.")
    lease=current.replace(microsecond=0)+timedelta(minutes=10)
    claim=db.execute(update(MockSession).where(
        MockSession.id==ident,MockSession.state==item.state,MockSession.expires_at==item.expires_at
    ).values(state="evaluating",expires_at=lease))
    if claim.rowcount!=1:
        db.rollback()
        raise HTTPException(409,"Trạng thái chấm điểm vừa thay đổi. Hãy tải lại.")
    # Commit the claim before the model call. Usage logging writes through another connection.
    db.commit()
    leased=update(MockSession).where(MockSession.id==ident,MockSession.state=="evaluating",MockSession.expires_at==lease)
    try:
        answers=answers_for(db,ident)
        previous=db.scalar(select(Report.report).join(MockSession).where(MockSession.user_id==item.user_id,
            MockSession.role==item.role,MockSession.id!=ident,Report.report["version"].as_string()==report.VERSION
        ).order_by(Report.id.desc()).limit(1))
        db.commit()
        result=report.summarize(answers,item.plan,item.role,previous["score"] if previous else None,actor["id"])
        completed=db.execute(leased.values(state="finished"))
        if completed.rowcount!=1:
            raise HTTPException(409,"Lượt chấm vừa thay đổi. Hãy tải lại báo cáo.")
        db.add(Report(session_id=ident,report=result))
        db.commit()
    except Exception:
        db.rollback()
        db.execute(leased.values(state="finished"))
        db.commit()
        raise
    db.refresh(item)
    return view(db,item)


def new_deadline():
    return now().replace(microsecond=0)+timedelta(seconds=QUESTION_SECONDS)


def initialize_deadline(db,item):
    if item.state=="active" and item.question_deadline is None:
        db.execute(update(MockSession).where(MockSession.id==item.id,MockSession.state=="active",
                   MockSession.question_deadline.is_(None)).values(question_deadline=new_deadline()))
        db.commit()
        db.refresh(item)


def view(db,item):
    expire(db,item)
    initialize_deadline(db,item)
    q=None
    if item.state=="active":
        q=item.plan[item.cursor]
        q={**{k:q[k] for k in ("question","kind")},"seconds":QUESTION_SECONDS}
        if item.followups:
            q["question"]=item.plan[item.cursor]["followup"]
    result=saved_report(db,item.id) if item.state in {"finished","expired"} else None
    return {"id":item.id,"role":item.role,"state":item.state,"cursor":item.cursor,"turn":item.followups,
            "total":len(item.plan),"question":q,"expires_at":item.expires_at,"report":result,"mode":AI_BACKEND,
            "source":item.plan[0].get("source") if item.plan else None,
            "remaining_ms":max(0,int((item.question_deadline-now()).total_seconds()*1000)) if q else None,
            "evaluation_pending":result is None and item.state in {"finished","expired","evaluating"}}

def history(db,actor):
    allow(actor,"student")
    items=list(db.scalars(select(MockSession).where(MockSession.user_id==actor["id"])
                         .order_by(MockSession.id.desc()).limit(20)))
    return [view(db,s) for s in items]

def start(db,actor,data):
    allow(actor,"student")
    count=db.scalar(select(func.count()).select_from(MockSession).where(
        MockSession.user_id==actor["id"],MockSession.created_at>=now().replace(hour=0,minute=0,second=0,microsecond=0)))
    if count>=DAILY_MOCKS:
        raise HTTPException(429,"Đã đạt số buổi luyện hôm nay")
    job_id=data.job_id
    if data.question_set_id is not None:
        job_id,role,plan=snapshot(db,data.question_set_id)
        if data.job_id is not None and data.job_id!=job_id:
            raise HTTPException(422,"Bộ câu hỏi không thuộc vị trí đã chọn")
    else:
        role=data.role.strip()
        questions=[{"code":q.code,"question":q.question,"kind":q.kind,"seconds":QUESTION_SECONDS,
                    "topic_criteria":[r["criterion"] for r in q.rubric]}
                   for q in db.scalars(select(Question).where(Question.role==role).order_by(Question.code))]
        if not questions:
            raise HTTPException(422,"Vai trò chưa có bộ câu hỏi")
        job=jobs.public_detail(db,job_id) if job_id else None
        jd={k:job[k] for k in ("title","requirements","skills","level")} if job else None
        profile=students.profile(db,actor)
        level=data.level or (jd["level"] if jd else "intern")
        profile["skills"]=[redact(skill,profile["name"]) for skill in profile["skills"]]
        db.commit()
        plan=planner.plan(role,questions,jd,profile,actor["id"],level=level)
    item=MockSession(user_id=actor["id"],role=role,job_id=job_id,state="active",plan=plan,
                     question_deadline=new_deadline(),expires_at=now()+timedelta(hours=24))
    db.add(item)
    db.commit()
    return view(db,item)

def abandon(db,actor,ident):
    item=session(db,actor,ident)
    expire(db,item)
    db.execute(update(MockSession).where(MockSession.id==ident,MockSession.state=="active").values(state="abandoned"))
    db.commit()
    return view(db,item)

def timeout(db,actor,ident,data):
    return submit(db,actor,ident,Submit(cursor=data.cursor,turn=data.turn,skip=True),timed_out=True)


def submit(db,actor,ident,data,*,timed_out=False):
    item=session(db,actor,ident)
    initialize_deadline(db,item)
    if item.state!="active" or item.expires_at<=now() or (data.cursor,data.turn)!=(item.cursor,item.followups):
        raise HTTPException(409,"Lượt trả lời đã thay đổi hoặc đã hết hạn")
    deadline=item.question_deadline
    expired=deadline<=now()
    if timed_out!=expired:
        raise HTTPException(409,"Đã hết thời gian trả lời câu này." if expired else "Câu hỏi vẫn còn thời gian.")
    text=redact(data.transcript.strip(),students.get_own(db,actor).name) if not data.skip else ""
    if not data.skip and (not text or not data.confirmed):
        raise HTTPException(422,"Hãy xác nhận nội dung câu trả lời")
    q=item.plan[item.cursor]
    prompt=q["followup"] if item.followups else q["question"]
    next_item=item.plan[item.cursor+1] if item.cursor+1<len(item.plan) else None
    turn=None
    company_question=bool(q.get("source"))
    if not data.skip and (not item.followups or (next_item and not company_question)):
        recent=[{"question":a.question,"answer":a.transcript[-500:]} for a in answers_for(db,ident)[-3:]]
        db.commit()
        try:
            turn=planner.next_turn(item.role,q,prompt,text,recent,None if company_question else next_item,
                                   not item.followups,actor["id"])
        except HTTPException as error:
            if error.status_code not in (429,503):
                raise
    needs_followup=bool(turn and len(turn.followup.strip())>=12 and not item.followups)
    cursor=item.cursor+int(not needs_followup)
    plan=list(item.plan)
    if needs_followup:
        plan[item.cursor]={**q,"followup":turn.followup.strip()}
    elif not company_question and next_item and turn and len(turn.next_question.strip())>=12:
        plan[cursor]={**next_item,"question":turn.next_question.strip()}
    state="finished" if cursor==len(plan) else "active"
    answer=Answer(session_id=ident,position=data.cursor,turn=data.turn,question=prompt,transcript=text,
                  transcript_confirmed=data.confirmed,evaluation={"skipped":data.skip,"timed_out":timed_out})
    changed=db.execute(update(MockSession).where(MockSession.id==ident,MockSession.cursor==data.cursor,
        MockSession.followups==data.turn,MockSession.state=="active",MockSession.expires_at>now(),
        MockSession.question_deadline==deadline).values(
        cursor=cursor,followups=int(needs_followup),state=state,plan=plan,
        question_deadline=new_deadline() if state=="active" else None))
    if changed.rowcount!=1:
        db.rollback()
        raise HTTPException(409,"Lượt trả lời đã thay đổi")
    db.add(answer)
    db.commit()
    db.refresh(item)
    return view(db,item)
