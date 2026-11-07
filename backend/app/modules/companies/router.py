from fastapi import APIRouter
from app.core.deps import Actor, DB
from . import service
from .schemas import CompanyInput

router = APIRouter(prefix="/api/companies", tags=["companies"])

@router.get("")
def list_companies(db: DB):
    return service.list_public(db)

@router.get("/mine")
def mine(db: DB, actor: Actor):
    return service.mine(db, actor)

@router.get("/{ident}")
def detail(ident: int, db: DB):
    return service.detail(db, ident)

@router.put("/{ident}")
def update(ident: int, data: CompanyInput, db: DB, actor: Actor):
    return service.save(db, actor, ident, data)

@router.put("/{ident}/follow")
def follow(ident: int, db: DB, actor: Actor, value: bool = True):
    return service.follow(db, actor, ident, value)
