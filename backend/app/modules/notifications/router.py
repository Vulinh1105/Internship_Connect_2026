from fastapi import APIRouter
from app.core.deps import Actor, DB
from . import service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("")
def mine(db: DB, actor: Actor):
    return service.list_mine(db, actor)

@router.post("/read")
def read(db: DB, actor: Actor):
    return service.mark_read(db, actor)
