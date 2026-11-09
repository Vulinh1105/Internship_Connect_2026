from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import func, select
from app.common import storage
from app.common.records import first, put, record, require
from .models import Company, Follow, Member
from . import repository as repo

LOGO_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}
LOGO_MAX = 2 * 1024 * 1024

def public(company):
    # Khóa lưu tệp logo nằm trong details; API công khai chỉ trả cờ has_logo.
    data = record(company)
    details = dict(data["details"] or {})
    data["has_logo"] = bool(details.pop("logo", None))
    data["details"] = details
    return data

def detail(db, ident):
    return public(require(repo.get_company(db, ident), "Không tìm thấy doanh nghiệp"))

def profile(db, ident, actor=None):
    # Trang công ty: thêm số người theo dõi và trạng thái theo dõi của người đang xem.
    data = detail(db, ident)
    data["followers"] = db.scalar(select(func.count()).select_from(Follow).where(Follow.company_id == ident)) or 0
    data["following"] = bool(actor and first(db, Follow, company_id=ident, user_id=actor["id"]))
    return data

def company_name(db, ident):
    return detail(db, ident)["name"]

def list_public(db):
    return [public(c) for c in db.scalars(select(Company).order_by(Company.name).limit(300))]

def followed(db, actor):
    from app.modules.jobs.models import Job
    from app.modules.jobs.repository import visible
    active = select(func.count(Job.id)).where(Job.company_id == Company.id, *visible()).correlate(Company).scalar_subquery()
    stmt = (select(Company, active).join(Follow, Follow.company_id == Company.id)
            .where(Follow.user_id == actor["id"]).order_by(Company.name))
    return [{**public(company), "active_jobs": count} for company, count in db.execute(stmt)]


def memberships(db, user_id):
    return list(db.scalars(select(Member.company_id).filter_by(user_id=user_id, active=True)))

def member_user_ids(db, company_id):
    return list(db.scalars(select(Member.user_id).filter_by(company_id=company_id, active=True)))

def follower_user_ids(db, company_id):
    # Người theo dõi, trừ chính thành viên công ty (họ đã biết tin của mình).
    members = set(member_user_ids(db, company_id))
    return [u for u in db.scalars(select(Follow.user_id).filter_by(company_id=company_id)) if u not in members]

def ensure_member(db, actor, company_id):
    if actor["role"] != "company_member" or company_id not in memberships(db, actor["id"]):
        raise HTTPException(403, "Bạn không thuộc doanh nghiệp sở hữu dữ liệu này")

def mine(db, actor):
    stmt = select(Member).filter_by(user_id=actor["id"],active=True)
    return [{**detail(db,row.company_id),"can_manage_members":row.manager} for row in db.scalars(stmt)]

def save(db, actor, ident, data):
    ensure_member(db, actor, ident)
    c = require(repo.get_company(db, ident))
    for field in ("name", "industry", "city", "description"):
        setattr(c, field, getattr(data, field))
    updates = data.model_dump(include={"address","work_schedule"},exclude_unset=True)
    if "address" in updates and updates["address"]!=c.details.get("address"):
        updates.update(address_is_synthetic=False,address_detail=None,district=None)
    c.details = {**c.details, "benefits": data.benefits, **updates}
    db.commit()
    return public(c)

def logo_kind(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None

def discard(key):
    if not key:
        return
    try:
        storage.resolve(key).unlink(missing_ok=True)
    except HTTPException:
        pass

def set_logo(db, actor, ident, data, filename):
    ensure_member(db, actor, ident)
    c = require(repo.get_company(db, ident))
    if not data or len(data) > LOGO_MAX:
        raise HTTPException(413, "Logo trống hoặc vượt quá 2 MB")
    kind = logo_kind(data)
    claimed = {".jpeg": ".jpg"}.get(Path(filename or "").suffix.lower(), Path(filename or "").suffix.lower())
    if kind is None or claimed != kind:
        raise HTTPException(415, "Logo phải là ảnh PNG, JPG hoặc WebP hợp lệ")
    key = storage.save(data, "logo" + kind, folder="company-logos", allowed=set(LOGO_TYPES), max_bytes=LOGO_MAX)
    old = c.details.get("logo")
    c.details = {**c.details, "logo": key}
    db.commit()
    discard(old)
    return public(c)

def remove_logo(db, actor, ident):
    ensure_member(db, actor, ident)
    c = require(repo.get_company(db, ident))
    old = c.details.get("logo")
    c.details = {k: v for k, v in c.details.items() if k != "logo"}
    db.commit()
    discard(old)
    return public(c)

def logo_file(db, ident):
    c = require(repo.get_company(db, ident), "Không tìm thấy doanh nghiệp")
    key = c.details.get("logo")
    if not key:
        raise HTTPException(404, "Doanh nghiệp chưa có logo")
    path = storage.resolve(key)
    return path, LOGO_TYPES.get(path.suffix.lower(), "application/octet-stream")

def follow(db, actor, company_id, value):
    detail(db, company_id)
    keys = dict(company_id=company_id, user_id=actor["id"])
    old = first(db, Follow, **keys)
    if value and old is None:
        put(db, Follow, keys)
    elif not value and old:
        db.delete(old)
    db.commit()
    return {"followed": value}
