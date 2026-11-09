import re

from app.ai.providers.embedding import normalize, words

MAJOR_GROUPS = (
    ("cong nghe thong tin","khoa hoc may tinh","ky thuat phan mem","he thong thong tin","khoa hoc du lieu",
     "computer science","software engineering","information technology","data science","data analyst","backend","software developer"),
    ("ke toan","kiem toan","accounting","audit"),
    ("tai chinh","ngan hang","finance","banking"),
    ("kinh doanh","quan tri kinh doanh","business administration","business development"),
    ("logistics","chuoi cung ung","supply chain"),
    ("marketing","truyen thong","content marketing"),
    ("nhan su","human resources","recruitment"),
    ("thiet ke","design","ui ux"),
    ("van hanh","operations"),
)


def phrase(needle, haystack):
    a, b = " ".join(words(needle)), " ".join(words(haystack))
    return bool(a and b and f" {a} " in f" {b} ")


def requirements(job):
    details = job.get("details") or {}
    required = {normalize(row["name"].strip()) for row in details.get("skill_priorities",[])
                if row["priority"]=="required"}
    skills = {}
    for skill in job["skills"]:
        skills.setdefault(normalize(skill.strip()),skill)
    return skills, required


def score(profile,job,similarity):
    skills = {normalize(skill.strip()) for skill in profile["skills"]}
    names, required = requirements(job)
    present = [label for key,label in names.items() if key in skills]
    missing = [label for key,label in names.items() if key not in skills]
    required = required & names.keys()
    preferred = names.keys()-required
    ratios = [(weight,len(group & skills)/len(group)) for weight,group in ((70,required),(30,preferred)) if group]
    skill_score = 40*sum(weight*ratio for weight,ratio in ratios)/sum(weight for weight,_ in ratios) if ratios else 0

    major, category = profile.get("major",""),job["category"]
    major_match = phrase(major,category) or phrase(category,major) or any(
        any(phrase(term,major) for term in group) and any(phrase(term,category) for term in group)
        for group in MAJOR_GROUPS)

    evidence = profile.get("experience_text","")
    experience = (job.get("details") or {}).get("experience") or ""
    related_evidence = any(phrase(label,evidence) for label in names.values()) or phrase(category,evidence)
    experience_score = 10 if related_evidence else 0
    if experience_score and re.search(r"\d+\s*(?:nam|thang|years?|months?)",normalize(experience)):
        # Nội dung liên quan là bằng chứng một phần khi chưa xác minh được số năm.
        experience_score = 5

    prefs = profile["preferences"]
    location = prefs.get("preferred_location","")
    mode = prefs.get("preferred_work_mode")
    salary = prefs.get("salary_min")
    target = prefs.get("target_category","")
    level = prefs.get("level")
    matches = [
        ("địa điểm",4,phrase(location,job["location"])),
        ("hình thức làm việc",4,bool(mode and mode==job["work_mode"])),
        ("mức lương",4,bool(salary is not None and job.get("salary_max") is not None and job["salary_max"]>=salary)),
        ("vị trí mong muốn",2,phrase(target,job["title"]) or phrase(target,category)),
        ("cấp độ",1,bool(level and level==job["level"])),
    ]
    components = {
        "skills":round(skill_score,1),
        "semantic":round(25*min(1,max(0,similarity or 0)),1),
        "major":10 if major_match else 0,
        "experience":experience_score,
        "preferences":sum(weight for _,weight,matched in matches if matched),
    }
    reasons = []
    if present:
        reasons.append(f"Khớp {len(present)}/{len(names)} kỹ năng")
    if major_match:
        reasons.append("ngành học liên quan")
    if experience_score:
        reasons.append("có dự án hoặc kinh nghiệm liên quan")
    matched_preferences = [label for label,_,matched in matches if matched]
    if matched_preferences:
        reasons.append("đáp ứng "+", ".join(matched_preferences))
    if components["semantic"]:
        reasons.append(f"nội dung hồ sơ tương đồng {components['semantic']}/25 điểm")
    return {"match_score":round(sum(components.values()),1),"matched_skills":present,"missing_skills":missing,
            "score_breakdown":components,"semantic_available":similarity is not None,
            "reason":" · ".join(reasons) or "Chưa có đủ bằng chứng phù hợp trong hồ sơ."}
