from sqlalchemy import select
from .models import Notification

def get_notification(db, ident):
    return db.get(Notification, ident)
