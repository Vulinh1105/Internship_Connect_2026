from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from app.core.deps import Actor, DB
from app.ai.providers import speech
from . import question_import, question_sets, schemas, service

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

@router.get("/question-sets/catalog")
def catalog(db:DB,actor:Actor):
    return question_sets.catalog(db,actor)

@router.get("/question-sets")
def my_question_sets(db:DB,actor:Actor):
    return question_sets.mine(db,actor)

@router.post("/question-sets",status_code=201)
def create_set(data:schemas.QuestionSetInput,db:DB,actor:Actor):
    return question_sets.save(db,actor,data)

@router.post("/question-sets/import",status_code=201)
def import_set(db:DB,actor:Actor,file:UploadFile=File(...),job_id:int|None=Form(None,gt=0),
               company_id:int|None=Form(None,gt=0),position_title:str|None=Form(None,max_length=200)):
    return question_import.import_draft(db,actor,job_id,file.filename or "",file.file.read(question_import.MAX_BYTES+1),
                                        company_id=company_id,position_title=position_title)

@router.put("/question-sets/{ident}")
def update_set(ident:int,data:schemas.QuestionSetInput,db:DB,actor:Actor):
    return question_sets.save(db,actor,data,ident)

@router.delete("/question-sets/{ident}")
def delete_set(ident:int,db:DB,actor:Actor):
    return question_sets.remove(db,actor,ident)

@router.post("/{ident}/timeout")
def timeout(ident:int,data:schemas.TurnCursor,db:DB,actor:Actor):
    return service.timeout(db,actor,ident,data)

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
    if item["remaining_ms"]<=0:
        raise HTTPException(409,"Đã hết thời gian trả lời câu này.")
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
