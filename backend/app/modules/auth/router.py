from fastapi import APIRouter, Request, Response
from app.core.deps import Actor, DB, OptionalActor
from app.core.rate_limit import enforce
from app.core.security import token
from . import service
from .schemas import Login, Register, Activate

router = APIRouter(prefix="/api/auth", tags=["auth"])

def set_session(response, user):
    response.set_cookie("career_session", token(user["id"]), max_age=28800, httponly=True, samesite="strict")
    return user

@router.post("/login")
def login(data: Login, db: DB, request: Request, response: Response):
    enforce(("login", request.client.host if request.client else "local"), 12, 60)
    return set_session(response, service.login(db, data.email, data.password))

@router.post("/register", status_code=201)
def register(data: Register, db: DB, request: Request, response: Response):
    enforce(("register", request.client.host if request.client else "local"), 6, 60)
    return set_session(response, service.register(db, data))

@router.get("/me")
def me(actor: OptionalActor):
    return actor

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("career_session", httponly=True, samesite="strict")
    return {"ok": True}

@router.get("/users")
def users(db: DB, actor: Actor):
    return service.list_users(db, actor)

@router.post("/users/{ident}/activate")
def activate(ident: int, data: Activate, db: DB, actor: Actor):
    return service.activate(db, actor, ident, data.password)
