from fastapi import APIRouter
from fastapi.responses import FileResponse
from app.core.deps import Actor,DB
from . import service
from .schemas import ApplyInput,Decision

router=APIRouter(prefix="/api/applications",tags=["applications"])

@router.post("",status_code=201)
def apply(data:ApplyInput,db:DB,actor:Actor):
    return service.apply(db,actor,data)

@router.get("/me")
def mine(db:DB,actor:Actor):
    return service.mine(db,actor)

@router.get("/job/{job_id}")
def applicants(job_id:int,db:DB,actor:Actor):
    return service.for_job(db,actor,job_id)

@router.patch("/{ident}/status")
def decision(ident:int,data:Decision,db:DB,actor:Actor):
    return service.decision(db,actor,ident,data.status,data.reason)

@router.get("/{ident}/cv")
def cv(ident:int,db:DB,actor:Actor):
    path,name=service.download(db,actor,ident)
    return FileResponse(path,filename=name)
