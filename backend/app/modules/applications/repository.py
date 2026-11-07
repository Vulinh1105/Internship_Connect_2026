from sqlalchemy import select
from .models import Application, ApplicationEvent

def get_application(db, ident):
    return db.get(Application, ident)

def get_applicationevent(db, ident):
    return db.get(ApplicationEvent, ident)
