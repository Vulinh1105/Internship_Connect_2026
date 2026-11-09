import logging
import secrets
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.common import storage
from app.common.records import first, put
from app.core import mailer
from app.core.config import now
from app.core.security import verify_password
from app.modules.companies.service import LOGO_MAX, LOGO_TYPES, discard, logo_kind
from .models import AccountSettings, EmailChange, User
from .service import RESET_TTL, _digest

log = logging.getLogger(__name__)
AVATAR_LIMIT = LOGO_MAX
NoticeGroup = Literal["applications","interviews","jobs","system"]
ProfileField = Literal["major","skills","school","specialization","study_year","summary"]


class SettingsInput(BaseModel):
    name: str = Field(default="",max_length=150)
    region: str = Field(default="",max_length=150)
    phone: str = Field(default="",max_length=30)
    notification_groups: list[NoticeGroup] = Field(max_length=4)
    email_groups: list[NoticeGroup] = Field(default_factory=list,max_length=4)
    job_alerts: bool = False
    profile_fields: list[ProfileField] = Field(max_length=6)


class EmailInput(BaseModel):
    email: str = Field(min_length=3,max_length=255,pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=1,max_length=128)


class TokenInput(BaseModel):
    token: str = Field(min_length=32,max_length=120)


class ClosureInput(BaseModel):
    action: Literal["disable","delete"]
    password: str = Field(min_length=1,max_length=128)


def options(db, user_id):
    row = db.get(AccountSettings, user_id)
    return row.options if row else {}


def update_options(db, user_id, changes):
    return put(db, AccountSettings, {"user_id":user_id}, options={**options(db,user_id),**changes})


def view(db, actor):
    data = options(db, actor["id"])
    return {**{key:value for key,value in data.items() if key!="avatar"},
            "has_avatar":bool(data.get("avatar")), "email_available":mailer.configured()}


def save(db, actor, data):
    update_options(db, actor["id"], data.model_dump())
    db.commit()
    return view(db, actor)


def avatar(db, actor, data=None, filename=""):
    old = options(db,actor["id"]).get("avatar")
    key = None
    if data is not None:
        from pathlib import Path
        kind = logo_kind(data)
        ext = Path(filename).suffix.lower().replace(".jpeg",".jpg")
        if not data or len(data)>AVATAR_LIMIT:
            raise HTTPException(413,"Ảnh trống hoặc vượt quá 2 MB")
        if kind is None or kind!=ext:
            raise HTTPException(415,"Chọn ảnh PNG, JPG hoặc WebP hợp lệ")
        key = storage.save(data,"avatar"+kind,folder="avatars",allowed=set(LOGO_TYPES),max_bytes=AVATAR_LIMIT)
    try:
        update_options(db,actor["id"],{"avatar":key})
        db.commit()
    except Exception:
        discard(key)
        raise
    discard(old)
    return view(db,actor)


def avatar_file(db, actor):
    key = options(db,actor["id"]).get("avatar")
    if not key:
        raise HTTPException(404,"Chưa có ảnh đại diện")
    path = storage.resolve(key)
    return path, LOGO_TYPES[path.suffix]


def verify(db, actor, password):
    if not verify_password(password, db.get(User,actor["id"]).password):
        raise HTTPException(403,"Mật khẩu hiện tại không đúng")


def start_email(db, actor, data):
    if not mailer.configured():
        raise HTTPException(503,"Hệ thống chưa cấu hình gửi email xác minh")
    verify(db,actor,data.password)
    email = data.email.strip().lower()
    if not mailer.deliverable(email):
        raise HTTPException(422,"Chưa thể gửi xác minh tới địa chỉ email này")
    if first(db,User,email=email):
        raise HTTPException(409,"Email đã được sử dụng")
    raw = secrets.token_urlsafe(32)
    put(db,EmailChange,{"user_id":actor["id"]},email=email,token_hash=_digest(raw),expires_at=now()+RESET_TTL)
    db.commit()
    return email,raw


def send_email(email, raw):
    try:
        mailer.send(email,"[Internship Connect] Xác minh địa chỉ email",
                    "Mở liên kết để xác minh email mới trong vòng một giờ: "+mailer.app_link("confirm-email/"+raw))
    except Exception as error:
        log.warning("Gửi email xác minh thất bại (%s)",type(error).__name__)


def finish_email(db, actor, raw):
    row = db.get(EmailChange,actor["id"])
    bad = HTTPException(400,"Liên kết xác minh không hợp lệ hoặc đã hết hạn")
    if not row or row.expires_at<=now() or not secrets.compare_digest(row.token_hash,_digest(raw)):
        raise bad
    email = row.email
    claimed = db.execute(delete(EmailChange).filter_by(user_id=actor["id"],token_hash=row.token_hash))
    if claimed.rowcount!=1:
        raise bad
    db.get(User,actor["id"]).email = email
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,"Email đã được sử dụng")
    return {"email":email}


def request_closure(db, actor, data):
    verify(db,actor,data.password)
    update_options(db,actor["id"],{"closure_request":data.action})
    db.commit()
    return {"ok":True}
