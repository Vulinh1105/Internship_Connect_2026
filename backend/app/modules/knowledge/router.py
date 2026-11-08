from fastapi import APIRouter,BackgroundTasks,File,Form,UploadFile
from app.core.deps import Actor,DB
from app.common.background import sync_pending
from . import service
from .schemas import DocumentInput

router=APIRouter(prefix="/api/knowledge",tags=["knowledge"])

@router.get("")
def list_documents(db:DB,actor:Actor):
    return service.list_all(db,actor)

@router.post("",status_code=201)
def add(data:DocumentInput,db:DB,actor:Actor,tasks:BackgroundTasks):
    result=service.publish(db,actor,data.title,data.content,topic=data.topic)
    tasks.add_task(sync_pending)
    return result

@router.post("/upload",status_code=201)
def upload(db:DB,actor:Actor,tasks:BackgroundTasks,file:UploadFile=File(),title:str=Form()):
    result=service.upload(db,actor,file.filename or "",file.file.read(service.MAX_UPLOAD_BYTES + 1),title)
    tasks.add_task(sync_pending)
    return result

@router.post("/{ident}/reprocess")
def reprocess(ident:int,db:DB,actor:Actor,tasks:BackgroundTasks):
    result=service.reprocess(db,actor,ident)
    tasks.add_task(sync_pending)
    return result

@router.delete("/{ident}")
def remove(ident:int,db:DB,actor:Actor,tasks:BackgroundTasks):
    result=service.remove(db,actor,ident)
    tasks.add_task(sync_pending)
    return result
