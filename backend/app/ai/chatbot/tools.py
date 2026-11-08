from fastapi import HTTPException
from app.ai.providers.embedding import words
from app.ai.rag.relevance import QUESTION_FILLER
from app.ai.matching.service import search_jobs,comparison
from app.modules.jobs import service as jobs
from app.modules.applications import service as applications
from app.modules.students import service as students

def search(db,actor,query,filters):
    requested=set(words(query))-QUESTION_FILLER-{
        "tim","viec","tin","goi","tuyen","dung","vi","tri","dang","cong","o","tai","thuc","tap",
    }
    rows=search_jobs(db,actor["id"],query,filters)
    return [
        job for job in rows if requested <= set(words(" ".join([
            job["title"],job["category"],job["location"],job["company_name"],
            job["work_mode"],job["level"]," ".join(job["skills"]),
            job["requirements"],job["description"],
        ])))
    ]


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
