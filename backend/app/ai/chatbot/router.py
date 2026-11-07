import json
from typing import Literal
from pydantic import BaseModel,Field
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.core.deps import Actor,DB
from . import service

class MessageInput(BaseModel):
    message:str=Field(min_length=2,max_length=500)
    job_ids:list[int]=Field(default_factory=list,max_length=5)

class FeedbackInput(BaseModel):
    rating:Literal[-1,1]
    comment:str=Field(default="",max_length=500)

router=APIRouter(prefix="/api/chat",tags=["chat"])

@router.post("/sessions",status_code=201)
def create(db:DB,actor:Actor):
    return service.create(db,actor)

@router.get("/sessions/{ident}/messages")
def history(ident:int,db:DB,actor:Actor):
    return service.history(db,actor,ident)

@router.post("/sessions/{ident}/messages")
def message(ident:int,data:MessageInput,db:DB,actor:Actor):
    result=service.respond(db,actor,ident,data)
    def events():
        for i in range(0,len(result["answer"]),45):
            yield "event: delta\ndata: "+json.dumps({"text":result["answer"][i:i+45]},ensure_ascii=False)+"\n\n"
        yield "event: result\ndata: "+json.dumps(result,ensure_ascii=False)+"\n\n"
    return StreamingResponse(events(),media_type="text/event-stream",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@router.post("/messages/{ident}/feedback")
def feedback(ident:int,data:FeedbackInput,db:DB,actor:Actor):
    return service.feedback(db,actor,ident,data)
