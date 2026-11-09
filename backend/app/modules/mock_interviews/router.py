from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from app.core.deps import Actor, DB
from app.ai.providers import speech
from . import schemas, service

router=APIRouter(prefix="/api/mock-interviews",tags=["Phỏng vấn ảo"])

@router.get("/roles")
def roles(db:DB):
    return service.roles(db)

@router.get("")
def history(db:DB,actor:Actor):
    return service.history(db,actor)

@router.post("")
def start(data:schemas.Start,db:DB,actor:Actor):
    return service.start(db,actor,data)

@router.get("/{ident}")
def get(ident:int,db:DB,actor:Actor):
    return service.view(db,service.session(db,actor,ident))

@router.post("/{ident}/answers")
def answer(ident:int,data:schemas.Submit,db:DB,actor:Actor):
    return service.submit(db,actor,ident,data)

@router.post("/{ident}/transcribe")
def transcribe(ident:int,db:DB,actor:Actor,file:UploadFile=File(...),consent:bool=Form(False)):
    item=get(ident,db,actor)
    if item["state"]!="active" or not consent:
        raise HTTPException(422,"Cần buổi luyện đang mở và đồng ý gửi âm thanh")
    media_type=(file.content_type or "").split(";",1)[0].strip().lower()
    if media_type not in {"audio/webm","audio/ogg","audio/mpeg","audio/wav","audio/mp4"}:
        raise HTTPException(415,"Định dạng âm thanh không hỗ trợ")
    payload=file.file.read(8*1024*1024+1)
    if not payload or len(payload)>8*1024*1024:
        raise HTTPException(413,"Tệp âm thanh tối đa 8 MB")
    return {"transcript":speech.transcribe(actor["id"],file.filename or "answer.webm",payload)}

@router.get("/{ident}/speech")
def speak(ident:int,db:DB,actor:Actor):
    item=get(ident,db,actor)
    if not item["question"]:
        raise HTTPException(409,"Buổi luyện đã kết thúc")
    return Response(speech.speak(actor["id"],item["question"]["question"]),media_type="audio/mpeg")

@router.post("/{ident}/abandon")
def abandon(ident:int,db:DB,actor:Actor):
    return service.abandon(db,actor,ident)


@router.post("/{ident}/finish")
def finish(ident:int,db:DB,actor:Actor):
    return service.finish(db,actor,ident)


@router.post("/{ident}/evaluation")
def evaluate(ident:int,db:DB,actor:Actor):
    return service.evaluate(db,actor,ident)
