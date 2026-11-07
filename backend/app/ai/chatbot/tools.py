from fastapi import HTTPException
from app.ai.matching.service import search_jobs,comparison
from app.modules.jobs import service as jobs
from app.modules.applications import service as applications
from app.modules.students import service as students

def search(db,actor,query,filters):
    relax=[]
    current=dict(filters)
    result=search_jobs(db,actor["id"],query,current)
    for key,label in [("salary_min","mức phụ cấp"),("level","cấp bậc"),("location","địa điểm")]:
        if result:
            break
        if current.pop(key,None):
            relax.append(label)
            result=search_jobs(db,actor["id"],query,current)
    return result,relax

def job_details(db,ids):
    result=[]
    for ident in ids[:5]:
        try:
            result.append(jobs.public_detail(db,ident))
        except HTTPException as e:
            if e.status_code!=404:
                raise
    return result

def my_applications(db,actor,code=None):
    if actor["role"]!="student":
        raise HTTPException(403,"Chỉ sinh viên xem đơn của mình")
    return [{"id":x["id"],"title":x["job_title"],"status":x["status"]} for x in applications.mine(db,actor) if not code or x["code"]==code]

def cv_advice(db,actor,job_id):
    s=students.get_own(db,actor)
    profile=students.match_input(db,s.id)
    if not profile["cv_id"]:
        return "Hãy tải CV lên và xác nhận thông tin đã trích xuất trước."
    if not job_id:
        return "Chọn một tin thực tập để đối chiếu kỹ năng trong CV với yêu cầu."
    job=jobs.public_detail(db,job_id)
    result=comparison(profile,job)
    return "Kỹ năng đã có: "+(", ".join(result["matched_skills"]) or "chưa có kỹ năng trùng")+"\nKỹ năng cần bổ sung: "+(", ".join(result["missing_skills"]) or "không có")

def compare_jobs(db,actor,ids):
    rows=job_details(db,ids)
    if actor["role"]=="student" and rows:
        profile=students.match_input(db,students.get_own(db,actor).id)
        rows=[{**job,**comparison(profile,job)} for job in rows]
    return rows
