from fastapi import APIRouter
from app.core.deps import Actor,DB
from . import service
from .schemas import Invitation,Reply

router=APIRouter(prefix="/api/interviews",tags=["interviews"])

@router.get("")
def mine(db:DB,actor:Actor):
    return service.mine(db,actor)

@router.post("",status_code=201)
def invite(data:Invitation,db:DB,actor:Actor):
    return service.invite(db,actor,data)

@router.post("/{ident}/respond")
def respond(ident:int,data:Reply,db:DB,actor:Actor):
    return service.reply(db,actor,ident,data)

@router.post("/{ident}/cancel")
def cancel(ident:int,db:DB,actor:Actor):
    return service.cancel(db,actor,ident)
