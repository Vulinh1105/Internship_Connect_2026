from datetime import timedelta
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
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.main import app
from app.core.config import now
from app.core.database import Base, Session, engine
from app.ai.vector import client as vectors, sync
from app.modules.jobs.models import Job
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

def test_complete_flows():
    try:
        initialize()
        verify_flows()
    finally:
        vectors.close()
        engine.dispose()
        sandbox.cleanup()

def verify_flows():
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
    assert len(payload(student.get("/api/matching")))>0
    company_id=payload(company.get("/api/companies/mine"))[0]["id"]
    job=payload(company.post("/api/jobs",json={"company_id":company_id,"title":"Thuc tap SQL Python",
         "description":"Phan tich du lieu SQL Python va viet bao cao kiem thu.",
         "requirements":"Kien thuc SQL","category":"Data","location":"Ha Noi","work_mode":"hybrid",
         "skills":["SQL","Python"],"deadline":(now()+timedelta(days=30)).date().isoformat()}),201)
    jid=job["id"]
    assert guest.get(f"/api/jobs/{jid}").status_code==404
    assert student.post(f"/api/jobs/{jid}/review",json={"decision":"approved"}).status_code==403
    payload(staff.post(f"/api/jobs/{jid}/review",json={"decision":"approved"}))
    assert payload(guest.get(f"/api/jobs/{jid}"))["active"]
    assert vectors.entries("jobs",vectors.filters(entity_id=jid))
    cv=payload(student.post("/api/students/me/cvs",files={"file":("sample.txt",b"SQL and Python data analysis","text/plain")}),201)
    cv_id=cv["id"]
    payload(student.post(f"/api/students/me/cvs/{cv_id}/confirm",json={"skills":["SQL","Python"]}))
    assert company.get(f"/api/students/me/cvs/{cv_id}/download").status_code in {403,404}
    assert vectors.entries("cvs",vectors.filters(entity_id=cv_id))
    a=payload(student.post("/api/applications",json={"job_id":jid,"cv_id":cv_id}),201)
    aid=a["id"]
    assert student.post("/api/applications",json={"job_id":jid,"cv_id":cv_id}).status_code==409
    assert student.get(f"/api/applications/job/{jid}").status_code==403
    assert payload(company.get(f"/api/applications/job/{jid}"))[0]["id"]==aid
    assert company.get(f"/api/applications/{aid}/cv").status_code==200
    interview=payload(company.post("/api/interviews",json={"application_id":aid,
               "scheduled_at":(now()+timedelta(days=2)).isoformat(),"location":"Phong thu"}),201)
    iid=interview["id"]
    assert payload(student.post(f"/api/interviews/{iid}/respond",json={"action":"confirmed"}))["status"]=="confirmed"
    assert payload(company.patch(f"/api/applications/{aid}/status",json={"status":"accepted"}))["status"]=="accepted"
    assert len(payload(student.get("/api/notifications")))>=2
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
    while session["state"]=="active":
        session=payload(student.post(f"/api/mock-interviews/{sid}/answers",
            json={"cursor":session["cursor"],"turn":session["turn"],"skip":True}))
    assert session["state"]=="finished" and len(session["report"]["answers"])>=5

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
