import csv
import json
import os
from pathlib import Path
from collections import defaultdict
from datetime import date, datetime
from sqlalchemy import select
from app.core import metadata
from app.core.config import LOCAL_TZ, ROOT, now
from app.core.database import Session
from app.core.security import hash_password
from app.ai.vector.sync import enqueue
from app.modules.applications.models import Application, ApplicationEvent
from app.modules.auth.models import Grant, Permission, Role, User
from app.modules.companies.models import Company, Member
from app.modules.interviews.models import Interview
from app.modules.jobs.models import Job
from app.modules.jobs.service import close_job
from app.modules.knowledge.models import Document
from app.modules.mock_interviews.models import Question
from app.modules.notifications.models import Notification
from app.modules.students.models import Skill, Student
from scripts.seed_company_interviews import seed_company_interviews

SOURCE=ROOT/"data/seed/source"
DEMO_USERS={"USR-DEMO-S001","USR-DEMO-C001","USR-ADMIN-DEMO","USR-STAFF-DEMO"}

def rows(name):
    with (SOURCE/f"{name}.csv").open(encoding="utf-8-sig",newline="") as handle:
        yield from csv.DictReader(handle)

def insert(db,model,key,**values):
    item=db.scalar(select(model).filter_by(**key))
    if item:
        return item,False
    item=model(**key,**values)
    db.add(item)
    db.flush()
    return item,True

def ids(db,model):
    return dict(db.execute(select(model.code,model.id)).all())

def dt(text):
    if text:
        return datetime.fromisoformat(text).astimezone(LOCAL_TZ).replace(tzinfo=None)
    return None

def number(text):
    return int(text) if text else None

def enrich_details(item, fields, *, old_address=None):
    if not fields or item.details.get("seed_enriched_v3"):
        return
    fields = dict(fields)
    if isinstance(item, Company):
        address = fields.pop("address")
        if item.details.get("address") in (None, "", old_address):
            fields.update(address=address, address_is_synthetic=True)
        else:
            fields.pop("address_detail", None)
            fields.pop("district", None)
    item.details = {**fields, **item.details, "seed_enriched_v3": True}
    if "address" in fields:
        item.details = {**item.details, "address": fields["address"], "address_is_synthetic": True}


def retire_demo_jobs(db):
    codes = [row["seed_code"] for row in rows("core/internships") if row["seed_code"].startswith("DEMO-F-")]
    jobs = list(db.scalars(select(Job).where(Job.code.in_(codes),Job.deleted_at.is_(None))))
    for job in jobs:
        close_job(db,job,notify_applicants=False)
        job.deleted_at=now()
    return len(jobs)


def seed(db):
    retire_demo_jobs(db)
    company_extras = json.loads((SOURCE / "core/companies_v3.json").read_text(encoding="utf-8"))
    job_extras = json.loads((SOURCE / "core/internships_v3.json").read_text(encoding="utf-8"))
    for r in rows("access/roles"):
        insert(db,Role,{"code":r["role_code"]},label=r["label"])
    for r in rows("access/permissions"):
        insert(db,Permission,{"code":r["permission_code"]},description=r["description"])
    for r in rows("access/role_permissions"):
        insert(db,Grant,{"role":r["role_code"],"permission":r["permission_code"]})
    password=os.getenv("DEMO_PASSWORD","LocalDemo2026!")
    if len(password)<10:
        raise ValueError("DEMO_PASSWORD must contain at least 10 characters")
    for r in rows("access/users"):
        code=r["user_code"]
        active=code in DEMO_USERS
        insert(db,User,{"code":code},email=r["email"],role=r["role_code"],active=active,
               password=hash_password(password) if active else None)
    users=ids(db,User)
    for r in rows("core/companies"):
        company,_=insert(db,Company,{"code":r["seed_code"]},name=r["company_name"],industry=r["industry"],city=r["city"],
               description=r["description"],details={k:r[k] for k in ("address","website","company_size",
                    "founded_year","mission","culture","benefits","verification_status")})
        extras = dict(company_extras.get(r["seed_code"], {}))
        description = extras.pop("description", None)
        if description and company.description == r["description"] and not company.details.get("seed_enriched_v3"):
            company.description = description
        enrich_details(company, extras, old_address=r["address"])
    companies=ids(db,Company)
    for r in rows("access/company_members"):
        insert(db,Member,{"company_id":companies[r["company_seed_code"]],"user_id":users[r["user_code"]]},
               active=r["membership_status"]=="active",manager=r["membership_status"]=="active")
    skills={}
    for r in rows("core/skills"):
        insert(db,Skill,{"code":r["skill_id"]},name=r["skill_name"])
        skills[r["skill_id"]]=r["skill_name"]
    student_skills=defaultdict(list)
    for r in rows("core/student_skills"):
        student_skills[r["student_seed_code"]].append(skills[r["skill_id"]])
    for r in rows("core/students"):
        code=r["seed_code"]
        insert(db,Student,{"code":code},user_id=users[r["user_code"]],student_code=r["student_code"],name=r["full_name"],
               major=r["major"],summary=r["profile_summary"],skills=student_skills[code],
               details={k:r[k] for k in ("gpa","gpa_scale","gpa_scale_status","internship_status")})
    students=ids(db,Student)
    job_skills=defaultdict(list)
    for r in rows("core/internship_skills"):
        job_skills[r["job_seed_code"]].append({"name":skills[r["skill_id"]],"priority":r["priority"]})
    for r in rows("core/internships"):
        code=r["seed_code"]
        if code.startswith("DEMO-F-"):
            continue
        job,created=insert(db,Job,{"code":code},company_id=companies[r["company_seed_code"]],
             title=r["title"],description=r["description"],requirements=r["requirements"],category=r["category"],
             location=r["location"],work_mode=r["work_mode"],salary_min=number(r["salary_min_vnd"]),
             salary_max=number(r["salary_max_vnd"]),deadline=date.fromisoformat(r["deadline"]) if r["deadline"] else None,
             status=r["status"],moderation_status=r["moderation_status"],skills=[s["name"] for s in job_skills[code]],
             details={**{k:r[k] for k in ("currency","experience","education","quantity","working_hours",
                         "benefits","application_instructions","program_type","employment_schedule","pay_type",
                         "pay_period","fixture_case")},"skill_priorities":job_skills[code]})
        extras = job_extras.get(code)
        enriched = bool(extras and not job.details.get("seed_enriched_v3"))
        enrich_details(job, extras)
        if created or enriched:
            enqueue(db,"jobs",job.id)
    jobs=ids(db,Job)
    new_apps=set()
    for r in rows("demo/applications"):
        code=r["seed_code"]
        item,created=insert(db,Application,{"code":code},student_id=students[r["student_seed_code"]],
             job_id=jobs[r["job_seed_code"]],status=r["status"],cover_letter=r["cover_letter"],
             submitted_at=dt(r["submitted_at"]),decision_at=dt(r["decision_at"]))
        if created:
            new_apps.add(code)
    applications=ids(db,Application)
    for r in rows("demo/application_events"):
        code=r["application_seed_code"]
        if code in new_apps:
            db.add(ApplicationEvent(application_id=applications[code],actor_id=users[r["actor_user_code"]],
                   before=r["status_before"] or None,after=r["status_after"],occurred_at=dt(r["occurred_at"])))
    for r in rows("demo/interviews"):
        application_id=applications[r["application_seed_code"]]
        item,created=insert(db,Interview,{"code":r["seed_code"]},application_id=application_id,
             invited_by=users[r["invited_by"]],scheduled_at=dt(r["scheduled_at"]),location=r["location"],
             status=r["status"],note=r["note"],invited_at=dt(r["invited_at"]),cancelled_at=dt(r["cancelled_at"]),
             response=r["cancellation_reason"] or None)
        if created and item.status=="invited":
            application=db.get(Application,application_id)
            db.add(Notification(user_id=db.get(Student,application.student_id).user_id,kind="interview_invited",
                                message="Bạn có lịch phỏng vấn mô phỏng trong bộ dữ liệu.",target_id=item.id))
    for r in rows("ai/chatbot/document_catalog"):
        source=ROOT/"data/knowledge"/Path(r["relative_path"]).name
        doc,created=insert(db,Document,{"code":r["doc_id"]},title=r["title"],source=r["doc_id"],
              content=source.read_text(encoding="utf-8-sig"),version=r["version"],
              visibility=r["visibility"],status=r["status"],topic=r["source_type"])
        if created:
            enqueue(db,"knowledge",doc.id)
    rubrics=defaultdict(list)
    for r in rows("ai/virtual_interview/rubrics"):
        rubrics[r["question_id"],r["rubric_version"]].append({
            **{k:r[k] for k in ("criterion_id","criterion","score_0","score_1","score_2")},"weight":int(r["weight"])})
    for r in rows("ai/virtual_interview/questions"):
        version=r["rubric_version"]
        insert(db,Question,{"code":r["question_id"]},role=r["role"],question=r["question"],kind=r["question_type"],
               difficulty=r["difficulty"],seconds=int(r["time_limit_sec"]),version=version,
               rubric=rubrics[r["question_id"],version])
    seed_company_interviews(db,job_codes=[r["seed_code"] for r in rows("core/internships")])
    db.commit()

if __name__=="__main__":
    with Session() as db:
        seed(db)
        print("Seed complete:",{model.__tablename__:len(ids(db,model)) for model in (User,Company,Student,Job,Application,Document,Question)})
