from datetime import timedelta
from io import BytesIO
from types import SimpleNamespace
import base64
import os
from pathlib import Path
from tempfile import TemporaryDirectory

test_root=Path(__file__).resolve().parents[2]/"data/runtime"
test_root.mkdir(parents=True,exist_ok=True)
sandbox=TemporaryDirectory(dir=test_root,ignore_cleanup_errors=True)
os.environ.update(DATABASE_URL="sqlite:///"+(Path(sandbox.name)/"test.sqlite").as_posix(),
                  UPLOADS_PATH=str(Path(sandbox.name)/"uploads"),QDRANT_PATH=str(Path(sandbox.name)/"qdrant"),QDRANT_URL="",AI_BACKEND="local",
                  JWT_SECRET="isolated-tests-only-7ca02ebdd891d68bc61a")
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.main import app
from app.core.config import now
from app.core.database import Base, Session, engine
from app.ai.vector import client as vectors, sync
from app.ai.matching import service as matching
from app.ai.interview_engine import evaluator, planner, report
from app.ai.providers.model_config import OPENAI_DIMENSIONS
from app.ai.vector.collections import MATCHING_JOBS
from app.modules.jobs.models import Job
from app.modules.mock_interviews.models import MockSession
from app.modules.mock_interviews import question_import
from scripts.seed_db import seed

def initialize():
    Base.metadata.create_all(engine)
    with Session() as db:
        seed(db)
        seed(db)
        assert db.scalar(select(func.count()).select_from(Job))==106
        assert sync.drain(db,500)["failed"]==0

def actor(email):
    client=TestClient(app)
    response=client.post("/api/auth/login",json={"email":email+"@example.invalid","password":os.getenv("DEMO_PASSWORD","LocalDemo2026!")})
    assert response.status_code==200,response.text
    return client

def payload(response,status=200):
    assert response.status_code==status,response.text
    return response.json()

def fake_interview(schema,instruction,data,fallback,**options):
    assert options["force_openai"] is True
    if schema is planner.PlanWording:
        return schema(questions=[{"code":q["code"],"question":q["question"],"domains":planner.default_domains(q["kind"])}
                                 for q in data["questions"]])
    if schema is planner.NextTurn:
        return schema()
    summary={"strengths":[{"text":"Trả lời đúng trọng tâm","turn_ids":[1,2,999]}],
             "limitations":[],"practice":["Bổ sung ví dụ."]}
    if schema is evaluator.Summary:
        return schema.model_validate(summary)
    return schema.model_validate({"turns":[
        {"turn_id":t["turn_id"],"results":[{"domain":d,"scores":[8,7,6,5],
             "quote":t["transcript"][:50],"feedback":"Còn thiếu ví dụ."} for d in t["domains"]]}
        for t in data["turns"] if t["transcript"] and t["domains"]],
        "summary":summary if data["whole"] else None})


def test_long_interview_evaluation(monkeypatch):
    calls=[]
    def tracked(schema,instruction,data,fallback,**options):
        calls.append((options["feature"],len(data.get("turns",[]))))
        return fake_interview(schema,instruction,data,fallback,**options)
    monkeypatch.setattr(evaluator,"structured",tracked)
    plan=[{"kind":"technical","domains":["knowledge","problem_solving"]} for _ in range(6)]
    answers=[SimpleNamespace(position=i//2,turn=i%2,question=f"Câu hỏi {i}",transcript=f"Câu trả lời {i}",
                            evaluation={"skipped":False}) for i in range(11)]
    result=report.summarize(answers,plan,"Backend Intern",None,42)
    assert calls==[("interview_eval",10),("interview_eval",1),("interview_synthesis",0)]
    assert result["group_count"]==2 and result["score"]==65
    assert result["domains"]["knowledge"]["question_count"]==6
    assert result["strengths"][0]["turn_ids"]==[1,2]
    assert result["answers"][-1]["results"][0]["quote"]=="Câu trả lời 10"


def test_complete_flows(monkeypatch):
    def fake_openai(texts,user_id=None):
        return [[1.0]+[0.0]*(OPENAI_DIMENSIONS-1) for _ in texts]
    monkeypatch.setattr(sync,"OPENAI_API_KEY","mock")
    monkeypatch.setattr(matching,"OPENAI_API_KEY","mock")
    monkeypatch.setattr(sync,"embed_openai",fake_openai)
    monkeypatch.setattr(matching,"embed_openai",fake_openai)
    monkeypatch.setattr(planner,"structured",fake_interview)
    monkeypatch.setattr(evaluator,"structured",fake_interview)
    try:
        initialize()
        verify_flows(monkeypatch)
    finally:
        vectors.close()
        engine.dispose()
        sandbox.cleanup()

def verify_question_upload(company,student,jid,bank,monkeypatch):
    import pymupdf
    from docx import Document

    first = "Explain how an SQL index works."
    second = "Describe how you would check a slow query."
    with pymupdf.open() as pdf:
        page=pdf.new_page()
        page.insert_text((72,72),first+"\n"+second)
        pdf_bytes=pdf.tobytes()
    doc=Document()
    doc.add_table(rows=1,cols=1).cell(0,0).text=first
    doc.add_paragraph(second)
    word=BytesIO()
    doc.save(word)

    def extract(schema,instruction,data,fallback,**options):
        assert options["force_openai"] and options["feature"]=="interview_question_import"
        assert data["document"].index(first)<data["document"].index(second)
        return schema(questions=[{"question":question,"kind":"knowledge","difficulty":"basic",
                                  "guidance":"Invented guidance"} for question in (second,first)])
    monkeypatch.setattr(question_import,"structured",extract)
    endpoint=bank+"/import"
    def upload(client,filename,content):
        return client.post(endpoint,data={"job_id":str(jid)},files={"file":(filename,content)})
    assert upload(student,"interview.pdf",pdf_bytes).status_code==403
    assert upload(company,"interview.doc",b"old word").status_code==415
    for filename,data in (("interview.pdf",pdf_bytes),("interview.docx",word.getvalue())):
        draft=payload(upload(company,filename,data),201)
        assert draft["job_id"]==jid and draft["published"] is False
        assert [q["question"] for q in draft["questions"]]==[first,second]
        assert all(not q["guidance"] for q in draft["questions"])
        assert all(item["id"]!=draft["id"] for item in payload(student.get(bank+"/catalog")))
        payload(company.delete(f"{bank}/{draft['id']}"))
    company_id=payload(company.get("/api/companies/mine"))[0]["id"]
    actual_title=payload(company.get(f"/api/jobs/{jid}"))["title"]
    files={"file":("typed.txt",(first+"\n"+second).encode())}
    linked=payload(company.post(endpoint,data={"company_id":str(company_id),"position_title":actual_title},files=files),201)
    assert linked["job_id"]==jid and linked["job_title"]==actual_title
    payload(company.delete(f"{bank}/{linked['id']}"))
    position="Thực tập sinh Phân tích sản phẩm"
    fields={"company_id":str(company_id),"position_title":position}
    draft=payload(company.post(endpoint,data=fields,files=files),201)
    assert draft["job_id"] is None and draft["job_title"]==position and draft["company_id"]==company_id
    assert student.post(endpoint,data=fields,files=files).status_code==403
    updated=payload(company.put(f"{bank}/{draft['id']}",json={**draft,"published":True}))
    assert updated["published"] is True
    catalog=payload(student.get(bank+"/catalog"))
    assert any(item["id"]==draft["id"] and item["job_title"]==position for item in catalog)
    assert all(not item["job_title"].lower().startswith("tin demo") for item in catalog)
    session=payload(student.post("/api/mock-interviews",json={"question_set_id":draft["id"]}))
    assert session["source"]["job_title"]==position and session["question"]["question"]==first
    payload(company.delete(f"{bank}/{draft['id']}"))

    def invented(schema,*args,**kwargs):
        return schema(questions=[{"question":"An invented question.","kind":"knowledge","difficulty":"basic"}])
    monkeypatch.setattr(question_import,"structured",invented)
    assert upload(company,"interview.txt",first.encode()).status_code==503


def verify_flows(monkeypatch):
    guest=TestClient(app)
    assert guest.get("/app/").status_code==200
    assert guest.get("/app/src/pages/ai.js").status_code==200
    assert guest.get("/api/auth/me").json() is None
    assert guest.get("/api/applications/me").status_code==401
    visible=payload(guest.get("/api/jobs?limit=100"))
    assert visible["total"]>=95 and len(visible["items"])<=100
    assert all(j["active"] for j in visible["items"])
    with Session() as db:
        for j in db.scalars(select(Job).where(Job.moderation_status!="approved")):
            assert guest.get(f"/api/jobs/{j.id}").status_code==404

    student=actor("usr-demo-s001")
    company=actor("usr-demo-c001")
    staff=actor("staff-demo")
    assert student.get("/api/jobs/moderation").status_code==403
    assert staff.get("/api/auth/users").status_code==403
    assert MATCHING_JOBS!="jobs"
    assert vectors.entries(MATCHING_JOBS)
    matches=payload(student.get("/api/matching"))
    assert 0<len(matches)<=10
    assert all(j["semantic_available"] and j["score_breakdown"]["semantic"]==25 for j in matches)
    assert all(j["match_score"]==round(sum(j["score_breakdown"].values()),1) for j in matches)
    company_id=payload(company.get("/api/companies/mine"))[0]["id"]
    job=payload(company.post("/api/jobs",json={"company_id":company_id,"title":"Thuc tap SQL Python",
         "description":"Phan tich du lieu SQL Python va viet bao cao kiem thu.",
         "requirements":"Kien thuc SQL","category":"Data","location":"Ha Noi","work_mode":"hybrid",
         "skills":["SQL","Python"],"deadline":(now()+timedelta(days=30)).date().isoformat(),
         "experience":"6 thang","education":"Đại học trở lên","quantity":2,"employment_schedule":"full_time","address":"12 Tran Hung Dao"}),201)
    jid=job["id"]
    assert guest.get(f"/api/jobs/{jid}").status_code==404
    assert student.post(f"/api/jobs/{jid}/review",json={"decision":"approved"}).status_code==403
    assert student.get("/api/jobs/moderation/count").status_code==403
    assert payload(staff.get("/api/jobs/moderation/count"))["pending"]>=1
    payload(student.put(f"/api/companies/{company_id}/follow?value=true"))
    payload(staff.post(f"/api/jobs/{jid}/review",json={"decision":"approved"}))
    followed=[n for n in payload(student.get("/api/notifications")) if n["kind"]=="company_new_job" and n["target_id"]==jid]
    assert len(followed)==1 and "Thuc tap SQL Python" in followed[0]["message"]
    assert not any(n["kind"]=="company_new_job" for n in payload(company.get("/api/notifications")))
    assert payload(guest.get(f"/api/jobs/{jid}"))["active"]
    extra=payload(guest.get(f"/api/jobs/{jid}"))["details"]
    assert extra["quantity"]==2 and extra["education"]=="Đại học trở lên" and extra["address"]=="12 Tran Hung Dao"
    assert company.post("/api/jobs",json={"company_id":company_id,"title":"Sai hoc van","description":"Mo ta du dai de hop le.",
         "requirements":"Yeu cau","category":"Data","location":"Ha Noi","work_mode":"hybrid","education":"Tiến sĩ"}).status_code==422
    approved=[n for n in payload(company.get("/api/notifications")) if n["kind"]=="job_approved" and n["target_id"]==jid]
    assert approved and "Thuc tap SQL Python" in approved[0]["message"]
    assert vectors.entries("jobs",vectors.filters(entity_id=jid))
    cv=payload(student.post("/api/students/me/cvs",files={"file":("sample.txt",b"SQL and Python data analysis","text/plain")}),201)
    cv_id=cv["id"]
    payload(student.post(f"/api/students/me/cvs/{cv_id}/confirm",json={"skills":["SQL","Python"]}))
    assert company.get(f"/api/students/me/cvs/{cv_id}/download").status_code in {403,404}
    assert vectors.entries("cvs",vectors.filters(entity_id=cv_id))
    a=payload(student.post("/api/applications",json={"job_id":jid,"cv_id":cv_id}),201)
    aid=a["id"]
    assert student.post("/api/applications",json={"job_id":jid,"cv_id":cv_id}).status_code==409
    new_app=[n for n in payload(company.get("/api/notifications")) if n["kind"]=="application_new" and n["target_id"]==jid]
    assert len(new_app)==1 and "ứng tuyển" in new_app[0]["message"]
    assert not any(n["kind"]=="application_new" and n["target_id"]==jid for n in payload(student.get("/api/notifications")))
    assert student.get(f"/api/applications/job/{jid}").status_code==403
    assert payload(company.get(f"/api/applications/job/{jid}"))[0]["id"]==aid
    assert company.get(f"/api/applications/{aid}/cv").status_code==200
    interview=payload(company.post("/api/interviews",json={"application_id":aid,
               "scheduled_at":(now()+timedelta(days=2)).isoformat(),"location":"Phong thu"}),201)
    iid=interview["id"]
    assert payload(student.post(f"/api/interviews/{iid}/respond",json={"action":"confirmed"}))["status"]=="confirmed"
    assert payload(company.patch(f"/api/applications/{aid}/status",json={"status":"accepted"}))["status"]=="accepted"
    assert len(payload(student.get("/api/notifications")))>=2
    mine=payload(student.get("/api/notifications"))
    assert any("đã được nhận" in n["message"] for n in mine if n["kind"]=="application_status")
    unread=payload(student.get("/api/notifications/unread-count"))["unread"]
    assert unread>=2
    one=next(n for n in mine if n["read_at"] is None)
    assert company.post(f"/api/notifications/{one['id']}/read").status_code==404
    assert payload(student.post(f"/api/notifications/{one['id']}/read"))["unread"]==unread-1
    assert payload(student.post("/api/notifications/read"))["unread"]==0
    assert payload(student.get("/api/notifications/unread-count"))["unread"]==0
    bank="/api/mock-interviews/question-sets"
    verify_question_upload(company,student,jid,bank,monkeypatch)
    draft={"job_id":jid,"title":"Bộ câu hỏi Backend","description":"Kiểm thử",
        "questions":[{"question":"Bạn chọn chỉ mục SQL như thế nào?","kind":"both","difficulty":"basic","guidance":"Nội dung nội bộ"},
                     {"question":"Hãy mô tả cách đọc kế hoạch truy vấn.","kind":"knowledge","difficulty":"intermediate"}]}
    assert student.post(bank,json=draft).status_code==403
    created=payload(company.post(bank,json=draft),201)
    assert all(item["id"]!=created["id"] for item in payload(student.get(bank+"/catalog")))
    start_body={"question_set_id":created["id"],"job_id":jid}
    assert student.post("/api/mock-interviews",json=start_body).status_code==404
    url=f"{bank}/{created['id']}"
    payload(company.put(url,json={**draft,"published":True}))
    info=next(item for item in payload(student.get(bank+"/catalog")) if item["id"]==created["id"])
    assert info["question_count"]==2 and info["estimated_seconds"]==1200 and "questions" not in info
    company_session=payload(student.post("/api/mock-interviews",json=start_body))
    endpoint=f"/api/mock-interviews/{company_session['id']}"
    assert company_session["question"]["question"]==draft["questions"][0]["question"]
    assert company_session["question"]["seconds"]==600 and 590000<company_session["remaining_ms"]<=600000
    assert "Nội dung nội bộ" not in str(company_session)
    current={"cursor":0,"turn":0}
    assert student.post(endpoint+"/timeout",json=current).status_code==409
    with Session() as db:
        row=db.get(MockSession,company_session["id"])
        row.question_deadline=now()-timedelta(seconds=1)
        db.commit()
    assert payload(student.get(endpoint))["remaining_ms"]==0
    assert student.post(endpoint+"/answers",json={**current,"skip":True}).status_code==409
    next_question=payload(student.post(endpoint+"/timeout",json=current))
    assert next_question["cursor"]==1 and next_question["remaining_ms"]>590000
    assert student.post(endpoint+"/timeout",json=current).status_code==409
    payload(company.delete(url))
    assert all(item["id"]!=created["id"] for item in payload(student.get(bank+"/catalog")))
    assert payload(student.get(endpoint))["question"]["question"]==draft["questions"][1]["question"]
    payload(student.post(endpoint+"/finish"))
    result=payload(student.post(endpoint+"/evaluation"))["report"]
    assert result["answers"][0]["timed_out"] and result["answers"][0]["skipped"]

    payload(company.post(f"/api/jobs/{jid}/close"))
    assert guest.get(f"/api/jobs/{jid}").status_code==404
    assert not vectors.entries("jobs",vectors.filters(entity_id=jid))

    role=payload(student.get("/api/mock-interviews/roles"))[0]
    session=payload(student.post("/api/mock-interviews",json={"role":role}))
    sid=session["id"]
    assert company.get(f"/api/mock-interviews/{sid}").status_code==403
    assert student.post(f"/api/mock-interviews/{sid}/answers",json={"cursor":0,"turn":0,"transcript":"test"}).status_code==422
    first={"cursor":0,"turn":0,"transcript":"Tôi có kỹ năng SQL và mục tiêu thực hành qua một dự án cụ thể.","confirmed":True}
    session=payload(student.post(f"/api/mock-interviews/{sid}/answers",json=first))
    assert student.post(f"/api/mock-interviews/{sid}/answers",json=first).status_code==409
    assert session["report"] is None
    assert student.post(f"/api/mock-interviews/{sid}/evaluation").status_code==409
    while session["state"]=="active":
        session=payload(student.post(f"/api/mock-interviews/{sid}/answers",json={
            "cursor":session["cursor"],"turn":session["turn"],"confirmed":True,
            "transcript":"Tôi sẽ phân tích nguyên nhân và kiểm tra kết quả sau khi áp dụng."}))
    assert session["state"]=="finished" and session["report"] is None
    evaluation_endpoint=f"/api/mock-interviews/{sid}/evaluation"
    assert company.post(evaluation_endpoint).status_code==403
    def unavailable(*args,**kwargs):
        raise HTTPException(503,"Mô phỏng API không khả dụng")
    with monkeypatch.context() as patch:
        patch.setattr(evaluator,"structured",unavailable)
        assert student.post(evaluation_endpoint).status_code==503
    assert payload(student.get(f"/api/mock-interviews/{sid}"))["evaluation_pending"]
    result=payload(student.post(evaluation_endpoint))["report"]
    assert result["score"]==65 and result["group_count"]==1 and len(result["answers"])>=5
    assert result["domains"]["knowledge"]["score"]==result["domains"]["problem_solving"]["score"]==65
    assert payload(student.post(evaluation_endpoint))["report"]==result

    chat=payload(student.post("/api/chat/sessions"),201)["id"]
    assert company.get(f"/api/chat/sessions/{chat}/messages").status_code==404
    response=student.post(f"/api/chat/sessions/{chat}/messages",json={"message":"Điều kiện công khai tin là gì?"})
    assert response.status_code==200 and "event: result" in response.text
    result=payload(student.get(f"/api/chat/sessions/{chat}/messages"))[-1]
    assert result["meta"]["sources"],result
    payload(student.post(f"/api/chat/messages/{result['id']}/feedback",json={"rating":1}))
    response=student.post(f"/api/chat/sessions/{chat}/messages",json={"message":"Chi tiết tin này","job_ids":[999999]})
    assert response.status_code==200
    result=payload(student.get(f"/api/chat/sessions/{chat}/messages"))[-1]
    assert result["meta"]["jobs"]==[]
    verify_logo(company,company_id)

PNG=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")

def verify_logo(company,company_id):
    url=f"/api/companies/{company_id}/logo"
    guest=TestClient(app)
    assert guest.get(url).status_code==404
    assert payload(guest.get(f"/api/companies/{company_id}"))["has_logo"] is False
    assert guest.post(url,files={"file":("l.png",PNG,"image/png")}).status_code==401
    assert actor("usr-demo-s001").post(url,files={"file":("l.png",PNG,"image/png")}).status_code==403
    assert company.post(url,files={"file":("l.svg",b"<svg xmlns='http://www.w3.org/2000/svg'/>","image/svg+xml")}).status_code==415
    assert company.post(url,files={"file":("fake.png",b"khong phai anh","image/png")}).status_code==415
    assert company.post(url,files={"file":("khac.jpg",PNG,"image/jpeg")}).status_code==415
    assert company.post(url,files={"file":("big.png",PNG+b"0"*(2*1024*1024),"image/png")}).status_code==413
    done=payload(company.post(url,files={"file":("logo.png",PNG,"image/png")}))
    assert done["has_logo"] is True and "logo" not in done["details"]
    served=guest.get(url)
    assert served.status_code==200 and served.content==PNG
    assert served.headers["content-type"]=="image/png" and served.headers["cache-control"]=="no-cache"
    assert any(c["id"]==company_id and c["has_logo"] for c in payload(guest.get("/api/companies")))
    job=payload(guest.get("/api/jobs?limit=100"))["items"]
    assert any(j["company_id"]==company_id and j["company_has_logo"] for j in job)
    current=payload(company.get(f"/api/companies/{company_id}"))
    body={k:current[k] for k in ("name","industry","city","description")}|{"benefits":current["details"].get("benefits","")}
    assert payload(company.put(f"/api/companies/{company_id}",json=body))["has_logo"] is True
    replaced=payload(company.post(url,files={"file":("logo.jpeg",b"\xff\xd8\xff\xe0"+b"0"*20,"image/jpeg")}))
    assert replaced["has_logo"] is True and guest.get(url).headers["content-type"]=="image/jpeg"
    assert payload(company.delete(url))["has_logo"] is False
    assert guest.get(url).status_code==404
