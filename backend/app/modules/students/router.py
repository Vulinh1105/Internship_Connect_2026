from fastapi import APIRouter,BackgroundTasks,File,Form,UploadFile
from fastapi.responses import FileResponse
from app.common.background import sync_pending
from app.core.deps import Actor,DB
from . import service
from .schemas import ProfileInput,CVFacts

router=APIRouter(prefix="/api/students",tags=["students"])

@router.get("/me")
def profile(db:DB,actor:Actor):
    return service.profile(db,actor)

@router.put("/me")
def save(data:ProfileInput,db:DB,actor:Actor):
    return service.update_profile(db,actor,data)

@router.get("/skills")
def skills(db:DB):
    return service.skills_catalog(db)

@router.get("/me/cvs")
def cvs(db:DB,actor:Actor):
    return service.list_cvs(db,actor)

@router.post("/me/cvs",status_code=201)
def upload(db:DB,actor:Actor,file:UploadFile=File(),ai_consent:bool=Form(False)):
    return service.upload(db,actor,file.filename or "",file.file.read(5_000_001),ai_consent)

@router.post("/me/cvs/{ident}/confirm")
def confirm(ident:int,data:CVFacts,db:DB,actor:Actor,tasks:BackgroundTasks):
    result=service.confirm(db,actor,ident,data)
    tasks.add_task(sync_pending)
    return result

@router.get("/me/cvs/{ident}/download")
def download(ident:int,db:DB,actor:Actor):
    student=service.get_own(db,actor)
    path,name=service.file_for_student(db,student.id,ident)
    return FileResponse(path,filename=name)
