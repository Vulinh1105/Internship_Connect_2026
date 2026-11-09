from fastapi import APIRouter, BackgroundTasks, Request, Response
from app.core import mailer
from app.core.deps import Actor, DB, OptionalActor
from app.core.rate_limit import enforce
from app.core.security import token
from . import service
from .schemas import Login, Register, Activate, ChangePassword, ForgotPassword, ResetPassword

router = APIRouter(prefix="/api/auth", tags=["auth"])

def set_session(response, user, version=0):
    response.set_cookie("career_session", token(user["id"], version), max_age=28800, httponly=True, samesite="strict")
    return user

def client_key(request):
    return request.client.host if request.client else "local"

@router.post("/login")
def login(data: Login, db: DB, request: Request, response: Response):
    enforce(("login", request.client.host if request.client else "local"), 12, 60)
    user = service.login(db, data.email, data.password)
    return set_session(response, user, service.session_version(db, user["id"]))

@router.post("/register", status_code=201)
def register(data: Register, db: DB, request: Request, response: Response):
    enforce(("register", request.client.host if request.client else "local"), 6, 60)
    user = service.register(db, data)
    return set_session(response, user, service.session_version(db, user["id"]))

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

@router.post("/change-password")
def change_password(data: ChangePassword, db: DB, actor: Actor, response: Response):
    enforce(("change-password", actor["id"]), 5, 300)
    version = service.change_password(db, actor, data.current_password, data.new_password)
    set_session(response, actor, version)
    return {"ok": True}

@router.post("/forgot-password")
def forgot_password(data: ForgotPassword, db: DB, request: Request, tasks: BackgroundTasks):
    enforce(("forgot", client_key(request)), 6, 600)
    enforce(("forgot-email", data.email.strip().lower()), 3, 600)
    found = service.start_reset(db, data.email) if mailer.configured() else None
    if found:
        tasks.add_task(service.send_reset_mail, *found)
    # Luôn trả về cùng một kết quả để không lộ email nào đã đăng ký.
    return {"ok": True}

@router.post("/reset-password")
def reset_password(data: ResetPassword, db: DB, request: Request):
    enforce(("reset", client_key(request)), 10, 600)
    service.finish_reset(db, data.token, data.password)
    return {"ok": True}

@router.post("/users/{ident}/lock")
def lock(ident: int, db: DB, actor: Actor):
    return service.set_locked(db, actor, ident, True)

@router.post("/users/{ident}/unlock")
def unlock(ident: int, db: DB, actor: Actor):
    return service.set_locked(db, actor, ident, False)
