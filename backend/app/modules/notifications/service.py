import logging
from datetime import timedelta
from fastapi import HTTPException
from app.core import mailer
from sqlalchemy import func, select, update
from app.core.config import now
from app.common.records import record
from .models import Notification, NotificationEmail

log = logging.getLogger(__name__)

def send(db, user_id, kind, message, target_id=None):
    from app.modules.auth.settings import options
    group = next((group for prefix, group in (("application","applications"),("interview","interviews"),
                 ("job","jobs"),("company_new_job","jobs")) if kind.startswith(prefix)), "system")
    settings = options(db,user_id)
    groups = settings.get("notification_groups")
    if groups is None or group in groups:
        db.add(Notification(user_id=user_id, kind=kind, message=message[:400], target_id=target_id))
    if mailer.configured() and group in settings.get("email_groups",[]):
        db.add(NotificationEmail(user_id=user_id,message=message[:400]))

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


def matching_job_users(db,job):
    from app.ai.providers.embedding import words
    from app.modules.auth.models import AccountSettings, User
    from app.modules.students.models import Student

    rows = (select(Student.user_id,Student.preferences,AccountSettings.options)
            .join(AccountSettings,AccountSettings.user_id==Student.user_id)
            .join(User,User.id==Student.user_id).where(User.active.is_(True),User.locked_at.is_(None)))
    for ident,prefs,settings in db.execute(rows):
        if not settings.get("job_alerts"):
            continue
        target = set(words(prefs.get("target_category","")))
        place = set(words(prefs.get("preferred_location","")))
        mode = prefs.get("preferred_work_mode")
        salary = prefs.get("salary_min")
        if not (target or place or mode or salary):
            continue
        if target and not target.issubset(set(words(job.category+" "+job.title))):
            continue
        if place and not place.issubset(set(words(job.location))):
            continue
        if mode and mode!=job.work_mode:
            continue
        if salary and (job.salary_max is None or job.salary_max<salary):
            continue
        if prefs.get("level") and prefs["level"]!=job.level:
            continue
        yield ident


def deliver_pending(db,limit=5):
    if not mailer.configured():
        return
    from app.modules.auth.models import User
    stmt = (select(NotificationEmail).where(NotificationEmail.available_at<=now())
            .order_by(NotificationEmail.id).limit(1).with_for_update(skip_locked=True))
    for _ in range(limit):
        row = db.scalar(stmt)
        if not row:
            db.rollback()
            break
        user = db.get(User,row.user_id)
        try:
            if user and user.active and user.locked_at is None and mailer.deliverable(user.email):
                mailer.send(user.email,"[Internship Connect] Thông báo",
                            row.message+"\n\n"+mailer.app_link("notifications"))
        except Exception as error:
            row.attempts += 1
            row.available_at = now()+timedelta(minutes=5*row.attempts)
            log.warning("Gửi thông báo email thất bại (%s)",type(error).__name__)
            if row.attempts>=3:
                db.delete(row)
        else:
            db.delete(row)
        db.commit()
