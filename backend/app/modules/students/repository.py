from sqlalchemy import select
from .models import Student, Skill, CV

def get_student(db, ident):
    return db.get(Student, ident)

def get_skill(db, ident):
    return db.get(Skill, ident)

def get_cv(db, ident):
    return db.get(CV, ident)
