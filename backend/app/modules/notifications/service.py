from sqlalchemy import select, update
from app.core.config import now
from app.common.records import record
from .models import Notification

def send(db, user_id, kind, message, target_id=None):
    db.add(Notification(user_id=user_id, kind=kind, message=message[:400], target_id=target_id))

def list_mine(db, actor):
    return [record(n) for n in db.scalars(select(Notification).filter_by(user_id=actor["id"])
                                         .order_by(Notification.id.desc()).limit(100))]

def mark_read(db, actor):
    db.execute(update(Notification).where(Notification.user_id == actor["id"],
                                         Notification.read_at.is_(None)).values(read_at=now()))
    db.commit()
    return {"ok": True}
