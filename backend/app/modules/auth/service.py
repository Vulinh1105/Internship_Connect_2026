from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.common.records import first, record, require
from app.core.security import hash_password, verify_password
from . import repository as repo
from .models import User

def active_user(db, ident):
    item = repo.get_user(db, ident)
    return record(item, "id", "email", "role", "code") if item and item.active else None

def login(db, email, password):
    user = first(db, User, email=email.strip().lower())
    if not user or not user.active or not verify_password(password, user.password):
        raise HTTPException(401, "Email hoặc mật khẩu không hợp lệ, hoặc tài khoản chưa kích hoạt")
    return active_user(db, user.id)

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
    return [record(u, "id", "email", "role", "active", "code") for u in db.scalars(repo.select(User).order_by(User.id))]

def activate(db, actor, ident, password):
    if actor["role"] != "admin":
        raise HTTPException(403, "Chỉ admin được kích hoạt")
    u = require(repo.get_user(db, ident))
    if u.active:
        raise HTTPException(409, "Tài khoản đã hoạt động")
    u.password = hash_password(password)
    u.active = True
    db.commit()
    return record(u, "id", "email", "role", "active")
