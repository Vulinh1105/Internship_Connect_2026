from typing import Annotated
import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import claims
from app.modules.auth import service

DB = Annotated[Session, Depends(get_db)]

def optional_user(request: Request, db: DB):
    authorization = request.headers.get("authorization", "")
    value = authorization[7:] if authorization.lower().startswith("bearer ") else request.cookies.get("career_session")
    if not value:
        return None
    try:
        data = claims(value)
        return service.active_user(db, data["sub"], data["v"])
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        return None

def current_user(user=Depends(optional_user)):
    if user is None:
        raise HTTPException(401, "Vui lòng đăng nhập")
    return user

Actor = Annotated[dict, Depends(current_user)]
OptionalActor = Annotated[dict | None, Depends(optional_user)]

def allow(actor, *roles):
    if actor["role"] not in roles:
        raise HTTPException(403, "Bạn không có quyền thực hiện thao tác này")
