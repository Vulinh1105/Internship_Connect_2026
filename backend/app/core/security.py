import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import jwt
from app.core.config import RUNTIME

@lru_cache
def secret():
    configured = os.getenv("JWT_SECRET")
    if configured:
        if len(configured) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        return configured
    path = RUNTIME / "jwt.secret"
    try:
        with path.open("x", encoding="ascii") as file:
            file.write(secrets.token_hex(48))
        path.chmod(0o600)
    except FileExistsError:
        pass
    return path.read_text(encoding="ascii").strip()

def hash_password(value):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), bytes.fromhex(salt), 310000)
    return f"{salt}:{digest.hex()}"

def verify_password(value, stored):
    try:
        salt, digest = stored.split(":", 1)
        actual = hashlib.pbkdf2_hmac("sha256", value.encode(), bytes.fromhex(salt), 310000)
        return hmac.compare_digest(actual.hex(), digest)
    except (ValueError, AttributeError):
        return False

def token(user_id, version=0):
    return jwt.encode({"sub": str(user_id), "v": int(version), "exp": datetime.now(timezone.utc) + timedelta(hours=8)},
                      secret(), algorithm="HS256")

def claims(value):
    data = jwt.decode(value, secret(), algorithms=["HS256"], options={"require": ["exp", "sub"]})
    return {"sub": int(data["sub"]), "v": int(data.get("v", 0))}

def subject(value):
    return int(jwt.decode(value, secret(), algorithms=["HS256"], options={"require": ["exp", "sub"]})["sub"])
