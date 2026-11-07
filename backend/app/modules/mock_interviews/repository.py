from sqlalchemy import select
from .models import Question, MockSession, Answer, Report

def get_question(db, ident):
    return db.get(Question, ident)

def get_mocksession(db, ident):
    return db.get(MockSession, ident)

def get_answer(db, ident):
    return db.get(Answer, ident)

def get_report(db, ident):
    return db.get(Report, ident)
