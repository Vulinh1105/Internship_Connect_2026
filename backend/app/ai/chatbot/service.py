import re
from sqlalchemy import select
from time import perf_counter
from fastapi import HTTPException
from app.common.records import first,put,require
from app.core.rate_limit import enforce
from app.ai.usage import check
from app.ai.rag.retrieve import retrieve
from app.ai.rag.generate import answer
from app.modules.students import service as students
from app.modules.jobs import service as jobs
from . import intent,tools
from .models import ChatSession,Message,Feedback

def create(db,actor):
    item=ChatSession(user_id=actor["id"])
    db.add(item)
    db.commit()
    return {"id":item.id}

def own(db,actor,ident):
    return require(first(db,ChatSession,id=ident,user_id=actor["id"]),"Không tìm thấy hội thoại")

def history(db,actor,ident):
    own(db,actor,ident)
    return [{"id":m.id,"role":m.role,"text":m.text,"meta":m.meta}
            for m in db.scalars(select(Message).filter_by(session_id=ident).order_by(Message.id))]

def respond(db,actor,ident,data):
    session=own(db,actor,ident)
    enforce(("chat",actor["id"]),12)
    check(db,actor["id"])
    started=perf_counter()
    recent=history(db,actor,ident)
    profile={}
    if actor["role"]=="student":
        p=students.profile(db,actor)
        profile={"skills":p["skills"],"major":p["major"],"location":p["preferences"].get("preferred_location")}
    decision=intent.classify(actor["id"],data.message,[{"role":m["role"],"text":m["text"][:350]} for m in recent[-12:]],session.summary, bool(data.job_ids),profile)
    result={"answer":"","jobs":[],"sources":[],"action":None,"tools_used":[]}
    job_code=re.search(r"\bDEMO-(?:J\d+|F-[A-Z0-9-]+)\b",data.message.upper())
    app_code=re.search(r"\bDEMO-A\d+\b",data.message.upper())
    try:
        if job_code and decision.intent!="other":
            job,state=jobs.public_by_code(db,job_code.group(0))
            result["jobs"]=[job] if job else []
            result["answer"]={"active":"Tin đang nhận hồ sơ.","expired":"Tin đã hết hạn.",
                              "closed":"Tin đã đóng.","unavailable":"Không tìm thấy tin đang công khai."}[state]
            result["tools_used"]=["get_job"]
        elif decision.confidence<.6:
            result["answer"]="Bạn muốn tìm vị trí hoặc chủ đề nào cụ thể?"
        elif decision.intent=="job_search":
            filters=decision.entities.model_dump()
            if not filters["location"] and profile.get("location") and len(decision.query.split())<=6:
                filters["location"]=profile["location"]
            query=" ".join(decision.entities.skills) or decision.query
            if decision.query.strip().casefold().rstrip("?!.") in {"tìm việc","tìm việc cho tôi","gợi ý việc","tìm tin"}:
                if not profile.get("skills") and not filters["location"]:
                    result["answer"]="Bạn quan tâm ngành hoặc kỹ năng nào?"
                elif profile.get("skills"):
                    query=" ".join(profile["skills"])
            if not result["answer"]:
                result["jobs"],relax=tools.search(db,actor,query,filters)
                result["tools_used"]=["search_jobs"]
                result["answer"]=f"Tìm thấy {len(result['jobs'])} tin phù hợp." if result["jobs"] else "Chưa tìm thấy tin phù hợp."
                if relax:
                    result["answer"]+=" Đã mở rộng bộ lọc "+", ".join(relax)+"."
        elif decision.intent in {"job_detail","compare"}:
            result["jobs"]=tools.compare_jobs(db,actor,data.job_ids) if decision.intent=="compare" else tools.job_details(db,data.job_ids)
            result["tools_used"]=["get_job"]
            result["answer"]="Thông tin từ các tin đang công khai:" if result["jobs"] else "Chọn mã tin đang mở để xem. Tin đã đóng hoặc không tồn tại sẽ không có kết quả."
        elif decision.intent=="application_status":
            items=tools.my_applications(db,actor,app_code.group(0) if app_code else None)
            result["tools_used"]=["get_my_applications"]
            result["answer"]="\n".join(f"#{a['id']} · {a['title']} · {a['status']}" for a in items) or "Bạn chưa có đơn ứng tuyển."
        elif decision.intent=="cv_advice":
            result["answer"]=tools.cv_advice(db,actor,data.job_ids[0] if data.job_ids else None)
            result["tools_used"]=["compare_cv"]
        elif decision.intent=="knowledge":
            result.update(answer(actor["id"],decision.query,retrieve(db,actor["id"],decision.query)))
            result["tools_used"]=["retrieve_knowledge"]
        elif decision.intent=="mock" and actor["role"]=="student":
            result["answer"]="Bạn có thể chọn vị trí và bắt đầu phiên luyện tập."
            result["action"]="start_mock_interview"
        else:
            result["answer"]="Mình hỗ trợ tìm việc thực tập, tra cứu đơn, CV và luyện phỏng vấn."
    except HTTPException as e:
        if e.status_code==429:
            raise
        result["answer"]="Không lấy được dữ liệu lúc này." if e.status_code>=500 else str(e.detail)
    result.update(intent=decision.intent,latency_ms=int((perf_counter()-started)*1000))
    db.add(Message(session_id=ident,role="user",text=data.message))
    m=Message(session_id=ident,role="assistant",text=result["answer"],meta=result)
    db.add(m)
    if len(recent)>=20 and len(recent)%20==0:
        older=[x["text"][:150] for x in recent[:-12] if x["role"]=="user"]
        session.summary=" | ".join(older[-6:])
    db.commit()
    return {"id":m.id,**result}

def feedback(db,actor,ident,data):
    m=require(db.get(Message,ident))
    own(db,actor,m.session_id)
    if m.role!="assistant":
        raise HTTPException(422,"Chỉ đánh giá câu trả lời")
    put(db,Feedback,{"message_id":ident},rating=data.rating,comment=data.comment)
    db.commit()
    return {"ok":True}
