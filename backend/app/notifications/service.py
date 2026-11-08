from fastapi import HTTPException
from sqlalchemy import func, select, update
from app.core.config import now
from app.common.records import record
from .models import Notification

def send(db, user_id, kind, message, target_id=None):
    db.add(Notification(user_id=user_id, kind=kind, message=message[:400], target_id=target_id))

def send_many(db, user_ids, kind, message, target_id=None):
    for user_id in dict.fromkeys(user_ids):
        send(db, user_id, kind, message, target_id)

def list_mine(db, actor):
    return [record(n) for n in db.scalars(select(Notification).filter_by(user_id=actor["id"])
                                         .order_by(Notification.id.desc()).limit(100))]

def unread_count(db, actor):
    count = db.scalar(select(func.count()).select_from(Notification)
                      .where(Notification.user_id == actor["id"], Notification.read_at.is_(None)))
    return {"unread": count or 0}

def mark_one_read(db, actor, ident):
    n = db.get(Notification, ident)
    if n is None or n.user_id != actor["id"]:
        raise HTTPException(404, "Không tìm thấy thông báo")
    if n.read_at is None:
        n.read_at = now()
        db.commit()
    return {"ok": True, **unread_count(db, actor)}

def mark_read(db, actor):
    db.execute(update(Notification).where(Notification.user_id == actor["id"],
                                         Notification.read_at.is_(None)).values(read_at=now()))
    db.commit()
    return {"ok": True, "unread": 0}
