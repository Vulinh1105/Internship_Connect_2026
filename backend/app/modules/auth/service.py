import hashlib
import logging
import secrets
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from app.common.records import first, record, require
from app.core import mailer
from app.core.config import now
from app.core.security import hash_password, verify_password
from . import repository as repo
from .models import PasswordReset, User

log = logging.getLogger(__name__)
RESET_TTL = timedelta(hours=1)

def active_user(db, ident, version=None):
    item = repo.get_user(db, ident)
    if not item or not item.active or item.locked_at is not None:
        return None
    if version is not None and (item.session_version or 0) != version:
        return None
    return record(item, "id", "email", "role", "code")

def session_version(db, ident):
    return (repo.get_user(db, ident).session_version or 0)

def login(db, email, password):
    user = first(db, User, email=email.strip().lower())
    if not user or not verify_password(password, user.password):
        raise HTTPException(401, "Email hoặc mật khẩu không hợp lệ, hoặc tài khoản chưa kích hoạt")
    if user.locked_at is not None:
        raise HTTPException(403, "Tài khoản đã bị khóa. Hãy liên hệ quản trị viên.")
    if not user.active:
        raise HTTPException(401, "Email hoặc mật khẩu không hợp lệ, hoặc tài khoản chưa kích hoạt")
    return active_user(db, user.id)

def change_password(db, actor, current, new):
    user = require(repo.get_user(db, actor["id"]))
    if not verify_password(current, user.password):
        raise HTTPException(403, "Mật khẩu hiện tại không đúng")
    if verify_password(new, user.password):
        raise HTTPException(422, "Mật khẩu mới phải khác mật khẩu hiện tại")
    user.password = hash_password(new)
    # Tăng phiên bản để mọi phiên đăng nhập cũ (ở thiết bị khác) hết hiệu lực.
    user.session_version = (user.session_version or 0) + 1
    db.commit()
    return user.session_version

def _digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def start_reset(db, email):
    # Trả về (email, token) nếu có thể gửi liên kết; không báo cho người gọi biết tài khoản có tồn tại hay không.
    user = first(db, User, email=email.strip().lower())
    if not user or not user.active or user.locked_at is not None or not mailer.deliverable(user.email):
        return None
    for old in db.scalars(select(PasswordReset).where(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None))):
        old.used_at = now()
    raw = secrets.token_urlsafe(32)
    db.add(PasswordReset(user_id=user.id, token_hash=_digest(raw), expires_at=now() + RESET_TTL))
    db.commit()
    return user.email, raw

def send_reset_mail(email, token):
    try:
        mailer.send(email, "[Internship Connect] Đặt lại mật khẩu",
            "Bạn (hoặc ai đó) vừa yêu cầu đặt lại mật khẩu cho tài khoản này.\n\n"
            f"Mở liên kết sau để đặt mật khẩu mới (có hiệu lực 1 giờ, dùng được một lần):\n{mailer.app_link('reset/' + token)}\n\n"
            "Nếu không phải bạn yêu cầu, hãy bỏ qua email này; mật khẩu hiện tại vẫn giữ nguyên.")
    except Exception as error:
        log.warning("Không gửi được email đặt lại mật khẩu (%s)", type(error).__name__)

def finish_reset(db, token, password):
    bad = HTTPException(400, "Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn")
    row = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == _digest(token)))
    if not row or row.used_at is not None or row.expires_at < now():
        raise bad
    user = repo.get_user(db, row.user_id)
    if not user or not user.active or user.locked_at is not None:
        raise bad
    # Đánh dấu đã dùng bằng một câu lệnh có điều kiện để hai yêu cầu cùng lúc không cùng thành công.
    claimed = db.execute(update(PasswordReset).where(PasswordReset.id == row.id, PasswordReset.used_at.is_(None)).values(used_at=now()))
    if claimed.rowcount != 1:
        raise bad
    user.password = hash_password(password)
    user.session_version = (user.session_version or 0) + 1
    db.commit()

def set_locked(db, actor, ident, locked):
    if actor["role"] != "admin":
        raise HTTPException(403, "Chỉ admin được khóa hoặc mở khóa")
    user = require(repo.get_user(db, ident))
    if locked:
        if user.id == actor["id"]:
            raise HTTPException(409, "Không thể tự khóa tài khoản của mình")
        if user.locked_at is not None:
            raise HTTPException(409, "Tài khoản đã bị khóa")
        if not user.active:
            raise HTTPException(409, "Tài khoản chưa kích hoạt")
        user.locked_at = now()
    else:
        if user.locked_at is None:
            raise HTTPException(409, "Tài khoản không bị khóa")
        user.locked_at = None
    db.commit()
    return {**record(user, "id", "email", "role", "active", "code"), "locked": user.locked_at is not None}

def register(db, data):
    from app.modules.students import service as students
    email = data.email.strip().lower()
    if "@" not in email or email.endswith("@example.invalid"):
        raise HTTPException(422, "Email không hợp lệ")
    if first(db, User, email=email):
        raise HTTPException(409, "Email đã đăng ký")
    user = User(email=email, password=hash_password(data.password), role="student", active=True)
    db.add(user)
    try:
        db.flush()
        students.create_profile(db, user.id, data.name.strip())
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email đã đăng ký")
    return active_user(db, user.id)

def list_users(db, actor):
    if actor["role"] != "admin":
        raise HTTPException(403, "Chỉ admin được quản lý tài khoản")
    return [{**record(u, "id", "email", "role", "active", "code"), "locked": u.locked_at is not None}
            for u in db.scalars(repo.select(User).order_by(User.id))]

def activate(db, actor, ident, password):
    if actor["role"] != "admin":
        raise HTTPException(403, "Chỉ admin được kích hoạt")
    u = require(repo.get_user(db, ident))
    if u.active or u.locked_at is not None:
        raise HTTPException(409, "Tài khoản đã hoạt động")
    u.password = hash_password(password)
    u.active = True
    db.commit()
    return record(u, "id", "email", "role", "active")
