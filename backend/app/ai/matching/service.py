import logging
from fastapi import HTTPException
from app.ai.providers.embedding import embed,words
from app.ai.vector import client as vectors
from app.modules.jobs import service as jobs
from app.modules.students import service as students
from .ranking import score

log=logging.getLogger(__name__)

def search_jobs(db,user_id,query,filters=None):
    filters={k:v for k,v in (filters or {}).items() if k in {"location","level","category","work_mode","salary_min","salary_max"} and v not in ("",None)}
    allowed={j["id"]:j for j in jobs.search(db,limit=100,**filters)["items"]}
    lexical=jobs.search(db,q=query,limit=40,**filters)["items"]
    rr={j["id"]:1/(60+i+1) for i,j in enumerate(lexical)}
    allowed.update((j["id"],j) for j in lexical)
    try:
        exact={k:filters[k] for k in ("work_mode","level") if k in filters}
        points=vectors.search("jobs",embed([query],user_id)[0],vectors.filters(status="active",**exact),limit=100)
        for i,p in enumerate(points):
            ident=p.payload["entity_id"]
            if ident in allowed and p.score>=0.10:
                rr[ident]=rr.get(ident,0)+1/(60+i+1)
    except HTTPException as error:
        if error.status_code==429:
            raise
        log.warning("Semantic job search using SQL fallback (%s)",error.status_code)
    except Exception as error:
        log.warning("Semantic job search using SQL fallback (%s)",type(error).__name__)
    terms=set(words(query))
    ranked=sorted(rr,key=lambda ident:rr[ident]+.005*len(terms & set(words(" ".join(allowed[ident]["skills"])))),reverse=True)
    return [allowed[ident] for ident in ranked[:5]]

def comparison(profile,job,similarity=None):
    if similarity is None:
        a=set(words(profile["text"]))
        b=set(words(job["title"]+" "+" ".join(job["skills"])))
        similarity=len(a&b)/max(1,len(a|b))
    return score(profile,job,similarity)

def vector_matches(profile,user_id,location="",job_ids=None):
    try:
        query=vectors.get_vector("cvs",profile["cv_id"]) if profile["cv_id"] else None
        if query is None:
            query=embed([profile["text"]],user_id)[0]
        points=vectors.search("jobs",query,vectors.job_filters(location=location,job_ids=job_ids),limit=100)
        return {p.payload["entity_id"]:p.score for p in points}
    except HTTPException as error:
        if error.status_code==429:
            raise
        log.warning("Matching using lexical fallback (%s)",error.status_code)
    except Exception as error:
        log.warning("Matching using lexical fallback (%s)",type(error).__name__)
    return {}

def score_application(db,actor,student_id,job,cv_id):
    profile=students.match_input(db,student_id,cv_id)
    try:
        found=vector_matches(profile,actor["id"],job_ids=[job["id"]])
    except HTTPException as error:
        if error.status_code!=429:
            raise
        found={}
    return comparison(profile,job,found.get(job["id"]))

def recommend(db,actor):
    from app.modules.applications import service as applications
    s=students.get_own(db,actor)
    profile=students.match_input(db,s.id)
    if not profile["text"].strip():
        raise HTTPException(422,"Thêm kỹ năng hoặc nguyện vọng để nhận gợi ý")
    done=applications.applied_ids(db,s.id)
    location=profile["preferences"].get("preferred_location","")
    allowed={j["id"]:j for j in jobs.search(db,location=location,limit=100)["items"] if j["id"] not in done}
    if not allowed:
        return []
    found=vector_matches(profile,actor["id"],job_ids=list(allowed))
    result=[{**j,**comparison(profile,j,found.get(ident))} for ident,j in allowed.items()]
    return sorted(result,key=lambda j:(-j["match_score"],j["id"]))[:10]
