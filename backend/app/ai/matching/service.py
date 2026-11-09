import logging
from fastapi import HTTPException
from sqlalchemy import select
from app.common.records import record
from app.core.config import OPENAI_API_KEY
from app.ai.providers.embedding import embed,embed_openai,normalize,words
from app.ai.vector import client as vectors
from app.ai.vector.collections import MATCHING_JOBS, collection
from app.modules.jobs import repository as job_repository
from app.modules.jobs import service as jobs
from app.modules.jobs.models import Job
from app.modules.students import service as students
from .ranking import requirements, score

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
    return score(profile,job,similarity)


def vector_matches(profile,user_id,job_ids):
    if not OPENAI_API_KEY:
        raise HTTPException(503,"AI Matching cần cấu hình OPENAI_API_KEY.")
    try:
        if not vectors.client().collection_exists(collection(MATCHING_JOBS)):
            return {}
        query = embed_openai([profile["text"]],user_id)[0]
        result = {}
        for start in range(0,len(job_ids),256):
            batch = job_ids[start:start+256]
            points = vectors.search(MATCHING_JOBS,query,vectors.job_filters(job_ids=batch),limit=len(batch))
            result.update((p.payload["entity_id"],p.score) for p in points)
        return result
    except HTTPException:
        raise
    except Exception as error:
        log.warning("Matching vector search unavailable (%s)",type(error).__name__)
        raise HTTPException(503,"Chưa truy vấn được dữ liệu AI Matching. Hãy thử lại sau.") from error


def score_application(db,actor,student_id,job,cv_id):
    profile = students.match_input(db,student_id,cv_id,hybrid=True)
    similarity = None
    if profile["text"].strip() and OPENAI_API_KEY:
        try:
            similarity = vector_matches(profile,actor["id"],[job["id"]]).get(job["id"])
        except HTTPException as error:
            if error.status_code not in (429,503):
                raise
    return comparison(profile,job,similarity)


def recommend(db,actor):
    from app.modules.applications import service as applications
    s = students.get_own(db,actor)
    profile = students.match_input(db,s.id,hybrid=True)
    if not profile["text"].strip():
        raise HTTPException(422,"Thêm kỹ năng hoặc nguyện vọng để nhận gợi ý")
    done = applications.applied_ids(db,s.id)
    stmt = select(Job).where(*job_repository.visible(),Job.id.not_in(done))
    skills = {normalize(skill.strip()) for skill in profile["skills"]}
    candidates = []
    for row in db.scalars(stmt):
        job = record(row)
        names, required = requirements(job)
        if (required & names.keys()) <= skills:
            candidates.append((row,job))
    if not candidates:
        return []
    found = vector_matches(profile,actor["id"],[row.id for row,_ in candidates])
    if not found:
        raise HTTPException(503,"Chỉ mục AI Matching chưa sẵn sàng. Hãy đồng bộ Qdrant rồi thử lại.")
    ranked = [(row,comparison(profile,job,found.get(row.id))) for row,job in candidates]
    ranked.sort(key=lambda pair:(-pair[1]["match_score"],pair[0].id))
    return [{**jobs.output(db,row),**result} for row,result in ranked[:10]]
