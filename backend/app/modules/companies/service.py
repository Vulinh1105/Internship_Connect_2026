from fastapi import HTTPException
from sqlalchemy import select
from app.common.records import first, put, record, require
from .models import Company, Follow, Member
from . import repository as repo

def detail(db, ident):
    return record(require(repo.get_company(db, ident), "Không tìm thấy doanh nghiệp"))

def company_name(db, ident):
    return detail(db, ident)["name"]

def list_public(db):
    return [record(c) for c in db.scalars(select(Company).order_by(Company.name).limit(300))]

def memberships(db, user_id):
    return list(db.scalars(select(Member.company_id).filter_by(user_id=user_id, active=True)))

def ensure_member(db, actor, company_id):
    if actor["role"] != "company_member" or company_id not in memberships(db, actor["id"]):
        raise HTTPException(403, "Bạn không thuộc doanh nghiệp sở hữu dữ liệu này")

def mine(db, actor):
    return [detail(db, i) for i in memberships(db, actor["id"])]

def save(db, actor, ident, data):
    ensure_member(db, actor, ident)
    c = require(repo.get_company(db, ident))
    for field in ("name", "industry", "city", "description"):
        setattr(c, field, getattr(data, field))
    c.details = {**c.details, "benefits": data.benefits}
    db.commit()
    return record(c)

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
