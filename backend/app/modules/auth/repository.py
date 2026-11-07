from sqlalchemy import select
from .models import User, Role, Permission, Grant

def get_user(db, ident):
    return db.get(User, ident)

def get_role(db, ident):
    return db.get(Role, ident)

def get_permission(db, ident):
    return db.get(Permission, ident)

def get_grant(db, ident):
    return db.get(Grant, ident)
