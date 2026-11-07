from fastapi import APIRouter, BackgroundTasks, Query
from app.core.deps import Actor, DB, OptionalActor
from app.common.background import sync_pending
from . import service
from .schemas import JobInput, ReviewInput

router=APIRouter(prefix="/api/jobs",tags=["jobs"])

@router.get("")
def search(db:DB,q:str="",location:str="",category:str="",work_mode:str="",level:str="",
           salary_min:int|None=None,salary_max:int|None=None,offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100)):
    return service.search(db,q=q[:200],location=location,category=category,work_mode=work_mode,level=level,
                          salary_min=salary_min,salary_max=salary_max,offset=offset,limit=limit)

@router.get("/semantic")
def semantic(db:DB,actor:Actor,q:str=Query(min_length=2,max_length=500),location:str=""):
    from app.ai.matching.service import search_jobs
    return search_jobs(db,actor["id"],q,{"location":location})

@router.get("/mine")
def mine(db:DB,actor:Actor):
    return service.mine(db,actor)

@router.get("/moderation")
def queue(db:DB,actor:Actor):
    return service.moderation_queue(db,actor)

@router.get("/saved")
def saved(db:DB,actor:Actor):
    return service.saved(db,actor)

@router.get("/{ident}")
def detail(ident:int,db:DB,actor:OptionalActor):
    return service.detail(db,ident,actor)

@router.post("",status_code=201)
def create(data:JobInput,db:DB,actor:Actor,tasks:BackgroundTasks):
    result=service.upsert(db,actor,data)
    tasks.add_task(sync_pending)
    return result

@router.put("/{ident}")
def update(ident:int,data:JobInput,db:DB,actor:Actor,tasks:BackgroundTasks):
    result=service.upsert(db,actor,data,ident)
    tasks.add_task(sync_pending)
    return result

@router.post("/{ident}/review")
def review(ident:int,data:ReviewInput,db:DB,actor:Actor,tasks:BackgroundTasks):
    result=service.review(db,actor,ident,data)
    tasks.add_task(sync_pending)
    return result

@router.post("/{ident}/close")
def close(ident:int,db:DB,actor:Actor,tasks:BackgroundTasks):
    result=service.close(db,actor,ident)
    tasks.add_task(sync_pending)
    return result

@router.delete("/{ident}")
def delete(ident:int,db:DB,actor:Actor,tasks:BackgroundTasks):
    result=service.close(db,actor,ident,True)
    tasks.add_task(sync_pending)
    return result

@router.put("/{ident}/saved")
def save(ident:int,db:DB,actor:Actor,value:bool=True):
    return service.save(db,actor,ident,value)
