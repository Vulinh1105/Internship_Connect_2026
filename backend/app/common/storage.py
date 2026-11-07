from uuid import uuid4
from pathlib import Path
from fastapi import HTTPException
from app.core.config import UPLOADS

def save(data, original_name, *, folder, allowed, max_bytes):
    ext = Path(original_name or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(415, "Định dạng tệp không được hỗ trợ")
    if not data or len(data) > max_bytes:
        raise HTTPException(413, "Tệp trống hoặc vượt giới hạn dung lượng")
    path = UPLOADS / folder / f"{uuid4().hex}{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path.relative_to(UPLOADS).as_posix()

def resolve(key):
    path = (UPLOADS / key).resolve()
    if not path.is_relative_to(UPLOADS.resolve()) or not path.is_file():
        raise HTTPException(404, "Tệp không còn tồn tại")
    return path
