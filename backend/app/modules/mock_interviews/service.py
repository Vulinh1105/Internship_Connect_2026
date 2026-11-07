from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import func, select, update
from app.ai.interview_engine import planner, evaluator, report
from app.common.file_parsing import redact
from app.core.config import AI_BACKEND, DAILY_MOCKS, now
from app.core.deps import allow
from app.modules.jobs import service as jobs
from app.modules.students import service as students
from .models import Answer, MockSession, Question, Report

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

def make_report(db,item,answers,user_id=None):
    previous=db.scalar(select(Report.report).join(MockSession).where(MockSession.user_id==item.user_id,
                       MockSession.role==item.role,MockSession.id!=item.id).order_by(Report.id.desc()).limit(1))
    return report.summarize(answers,previous["score"] if previous else None,user_id)

def expire(db,item):
    if item.state!="active" or item.expires_at>now():
        return
    changed=db.execute(update(MockSession).where(MockSession.id==item.id,MockSession.state=="active",
        MockSession.expires_at<=now()).values(state="expired"))
    if changed.rowcount==1:
        db.add(Report(session_id=item.id,report=make_report(db,item,answers_for(db,item.id))))
        db.commit()
    else:
        db.rollback()
        db.refresh(item)

def view(db,item):
    expire(db,item)
    q=None
    if item.state=="active":
        q=item.plan[item.cursor]
        q={k:q[k] for k in ("question","kind","seconds")}
        if item.followups:
            q["question"]=item.plan[item.cursor]["followup"]
    result=saved_report(db,item.id) if item.state in {"finished","expired"} else None
    return {"id":item.id,"role":item.role,"state":item.state,"cursor":item.cursor,"turn":item.followups,
            "total":len(item.plan),"question":q,"expires_at":item.expires_at,"report":result,"mode":AI_BACKEND}

def history(db,actor):
    allow(actor,"student")
    items=list(db.scalars(select(MockSession).where(MockSession.user_id==actor["id"])
                         .order_by(MockSession.id.desc()).limit(20)))
    return [view(db,s) for s in items]

def start(db,actor,data):
    allow(actor,"student")
    role=data.role.strip()
    questions=[{"code":q.code,"question":q.question,"kind":q.kind,"seconds":q.seconds,
                "rubric":q.rubric,"version":q.version}
               for q in db.scalars(select(Question).where(Question.role==role).order_by(Question.code))]
    if not questions:
        raise HTTPException(422,"Vai trò chưa có bộ câu hỏi")
    job=jobs.public_detail(db,data.job_id) if data.job_id else None
    jd={k:job[k] for k in ("title","requirements","skills","level")} if job else None
    count=db.scalar(select(func.count()).select_from(MockSession).where(
        MockSession.user_id==actor["id"],MockSession.created_at>=now().replace(hour=0,minute=0,second=0,microsecond=0)))
    if count>=DAILY_MOCKS:
        raise HTTPException(429,"Đã đạt số buổi luyện hôm nay")
    profile=students.profile(db,actor)
    plan=planner.plan(role,questions,jd,profile,actor["id"])
    item=MockSession(user_id=actor["id"],role=role,job_id=data.job_id,state="active",plan=plan,
                     expires_at=now()+timedelta(hours=24))
    db.add(item)
    db.commit()
    return view(db,item)

def abandon(db,actor,ident):
    item=session(db,actor,ident)
    expire(db,item)
    db.execute(update(MockSession).where(MockSession.id==ident,MockSession.state=="active").values(state="abandoned"))
    db.commit()
    return view(db,item)

def submit(db,actor,ident,data):
    item=session(db,actor,ident)
    if item.state!="active" or item.expires_at<=now() or (data.cursor,data.turn)!=(item.cursor,item.followups):
        raise HTTPException(409,"Lượt trả lời đã thay đổi hoặc đã hết hạn")
    text=redact(data.transcript.strip()) if not data.skip else ""
    if not data.skip and (not text or not data.confirmed):
        raise HTTPException(422,"Hãy xác nhận nội dung câu trả lời")
    q=item.plan[item.cursor]
    prompt=q["followup"] if item.followups else q["question"]
    evaluation,followup=evaluator.evaluate({**q,"question":prompt},text,actor["id"],data.skip)
    needs_followup=bool(followup and not data.skip and item.followups==0 and evaluation["score"]<75)
    cursor=item.cursor+int(not needs_followup)
    plan=list(item.plan)
    if needs_followup:
        plan[item.cursor]={**q,"followup":followup}
    state="finished" if cursor==len(plan) else "active"
    answer=Answer(session_id=ident,position=data.cursor,turn=data.turn,question=prompt,transcript=text,
                  transcript_confirmed=data.confirmed,evaluation=evaluation)
    summary=make_report(db,item,[*answers_for(db,ident),answer],actor["id"]) if state=="finished" else None
    changed=db.execute(update(MockSession).where(MockSession.id==ident,MockSession.cursor==data.cursor,
        MockSession.followups==data.turn,MockSession.state=="active",MockSession.expires_at>now()).values(
        cursor=cursor,followups=int(needs_followup),state=state,plan=plan))
    if changed.rowcount!=1:
        db.rollback()
        raise HTTPException(409,"Lượt trả lời đã thay đổi")
    db.add(answer)
    if summary:
        db.add(Report(session_id=ident,report=summary))
    db.commit()
    return view(db,item)
