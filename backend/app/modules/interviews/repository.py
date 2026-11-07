from sqlalchemy import select
from .models import Interview

def get_interview(db, ident):
    return db.get(Interview, ident)
