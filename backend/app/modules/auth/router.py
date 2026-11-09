from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from datetime import timedelta
from uuid import uuid4
from sqlalchemy import delete, select
from app.core.config import now
from app.common.records import record
from . import settings
from .models import LoginSession, User
from app.core import mailer
from app.core.deps import Actor, DB, OptionalActor
from app.core.rate_limit import enforce
from app.core.security import token
from . import service
from .schemas import Login, Register, Activate, ChangePassword, ForgotPassword, ResetPassword

router = APIRouter(prefix="/api/auth", tags=["auth"])

def set_session(db, request, response, user, version=0):
    ident = str(uuid4())
    db.add(LoginSession(id=ident, user_id=user["id"], version=version,
                        device=request.headers.get("user-agent", "")[:250], expires_at=now()+timedelta(hours=8)))
    db.commit()
    response.set_cookie("career_session", token(user["id"], version, ident), max_age=28800, httponly=True,
                        secure=request.url.scheme=="https", samesite="strict")
    return user

def client_key(request):
    return request.client.host if request.client else "local"

@router.post("/login")
def login(data: Login, db: DB, request: Request, response: Response):
    enforce(("login", request.client.host if request.client else "local"), 12, 60)
    user = service.login(db, data.email, data.password)
    return set_session(db, request, response, user, service.session_version(db, user["id"]))

@router.post("/register", status_code=201)
def register(data: Register, db: DB, request: Request, response: Response):
    enforce(("register", request.client.host if request.client else "local"), 6, 60)
    user = service.register(db, data)
    return set_session(db, request, response, user, service.session_version(db, user["id"]))

@router.get("/me")
def me(db: DB, actor: OptionalActor):
    if not actor:
        return None
    return {**{k:v for k,v in actor.items() if k!="session_id"},
            "has_avatar":bool(settings.options(db,actor["id"]).get("avatar"))}

@router.post("/logout")
def logout(response: Response, db: DB, actor: OptionalActor):
    if actor and actor.get("session_id"):
        db.execute(delete(LoginSession).filter_by(id=actor["session_id"], user_id=actor["id"]))
        db.commit()
    response.delete_cookie("career_session", httponly=True, samesite="strict")
    return {"ok": True}

@router.get("/users")
def users(db: DB, actor: Actor):
    return service.list_users(db, actor)

@router.post("/users/{ident}/activate")
def activate(ident: int, data: Activate, db: DB, actor: Actor):
    return service.activate(db, actor, ident, data.password)

@router.post("/change-password")
def change_password(data: ChangePassword, db: DB, actor: Actor, response: Response, request: Request):
    enforce(("change-password", actor["id"]), 5, 300)
    version = service.change_password(db, actor, data.current_password, data.new_password)
    set_session(db, request, response, {k:v for k,v in actor.items() if k!='session_id'}, version)
    return {"ok": True}

@router.post("/forgot-password")
def forgot_password(data: ForgotPassword, db: DB, request: Request, tasks: BackgroundTasks):
    if not mailer.configured():
        raise HTTPException(503, "Máy chủ chưa cấu hình gửi email đặt lại mật khẩu.")
    enforce(("forgot", client_key(request)), 6, 600)
    enforce(("forgot-email", data.email.strip().lower()), 3, 600)
    found = service.start_reset(db, data.email)
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


@router.get("/sessions")
def sessions(db: DB, actor: Actor):
    version = service.session_version(db, actor["id"])
    stmt = select(LoginSession).filter_by(user_id=actor["id"], version=version).where(LoginSession.expires_at > now())
    return [{**record(row,"id","device","created_at","expires_at"), "current": row.id==actor.get("session_id")}
            for row in db.scalars(stmt.order_by(LoginSession.created_at.desc()))]


@router.delete("/sessions/{ident}")
def revoke_session(ident: str, db: DB, actor: Actor, response: Response):
    changed = db.execute(delete(LoginSession).filter_by(id=ident,user_id=actor["id"]))
    if not changed.rowcount:
        raise HTTPException(404, "Không tìm thấy phiên đăng nhập")
    db.commit()
    if ident == actor.get("session_id"):
        response.delete_cookie("career_session", httponly=True, samesite="strict")
    return {"ok": True}


@router.post("/logout-others")
def logout_others(db: DB, actor: Actor, request: Request, response: Response):
    from sqlalchemy import update
    db.execute(update(User).where(User.id==actor["id"]).values(session_version=User.session_version+1))
    set_session(db, request, response, {k:v for k,v in actor.items() if k!='session_id'}, service.session_version(db,actor["id"]))
    return {"ok": True}


@router.get("/settings")
def get_settings(db: DB, actor: Actor):
    return settings.view(db,actor)


@router.put("/settings")
def save_settings(data: settings.SettingsInput, db: DB, actor: Actor):
    return settings.save(db,actor,data)


@router.post("/settings/avatar")
def avatar_upload(db: DB, actor: Actor, file: UploadFile=File()):
    return settings.avatar(db,actor,file.file.read(settings.AVATAR_LIMIT+1),file.filename or "")


@router.get("/settings/avatar")
def avatar_download(db: DB, actor: Actor):
    path, media = settings.avatar_file(db,actor)
    return FileResponse(path,media_type=media,headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"})


@router.delete("/settings/avatar")
def avatar_remove(db: DB, actor: Actor):
    return settings.avatar(db,actor)


@router.post("/settings/email")
def start_email(data: settings.EmailInput, db: DB, actor: Actor, tasks: BackgroundTasks):
    enforce(("email-change",actor["id"]),3,600)
    tasks.add_task(settings.send_email,*settings.start_email(db,actor,data))
    return {"ok":True}


@router.post("/settings/email/confirm")
def confirm_email(data: settings.TokenInput, db: DB, actor: Actor):
    enforce(("email-confirm",actor["id"]),10,600)
    return settings.finish_email(db,actor,data.token)


@router.post("/settings/closure")
def close_account(data: settings.ClosureInput, db: DB, actor: Actor):
    enforce(("closure",actor["id"]),5,300)
    return settings.request_closure(db,actor,data)
