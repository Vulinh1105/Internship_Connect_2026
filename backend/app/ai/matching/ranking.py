from app.ai.providers.embedding import normalize

def score(profile,job,similarity):
    skills={normalize(s) for s in profile["skills"]}
    present=[s for s in job["skills"] if normalize(s) in skills]
    missing=[s for s in job["skills"] if normalize(s) not in skills]
    prefs=profile["preferences"]
    level=float(job["level"] in {prefs.get("level","intern"),"intern"})
    location=not prefs.get("preferred_location") or normalize(prefs["preferred_location"])==normalize(job["location"])
    salary=not prefs.get("salary_min") or (job["salary_max"] or 0)>=prefs["salary_min"]
    sim=min(1,max(0,similarity))
    priorities={normalize(r["name"]):2 if r["priority"]=="required" else 1
                for r in job.get("details",{}).get("skill_priorities",[])}
    weights={s:priorities.get(normalize(s),1) for s in job["skills"]}
    ratio=sum(weights[s] for s in present)/max(1,sum(weights.values()))
    value=0.5*sim+0.3*ratio+0.1*level+0.1*(int(location)+int(salary))/2
    return {"match_score":round(value*100,1),"matched_skills":present,"missing_skills":missing,
            "reason":"Thiếu "+", ".join(missing) if missing else "Khớp các kỹ năng đã khai báo"}
