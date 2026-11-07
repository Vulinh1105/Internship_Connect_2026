from sqlalchemy import select
from .models import Company, Member, Follow

def get_company(db, ident):
    return db.get(Company, ident)

def get_member(db, ident):
    return db.get(Member, ident)

def get_follow(db, ident):
    return db.get(Follow, ident)
