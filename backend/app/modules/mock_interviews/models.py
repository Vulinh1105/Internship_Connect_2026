from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from app.core.config import now
from app.core.database import Base

class Question(Base):
    __tablename__ = "question_bank"
    id = Column(Integer, primary_key=True)
    code = Column(String(80), nullable=False, unique=True)
    role = Column(String(100), nullable=False)
    question = Column(Text, nullable=False)
    kind = Column(String(24), nullable=False)
    difficulty = Column(String(24), nullable=False)
    seconds = Column(Integer, nullable=False, default=180)
    rubric = Column(JSON, nullable=False)
    version = Column(String(30), nullable=False, default='1')

class MockSession(Base):
    __tablename__ = "interview_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    job_id = Column(Integer, ForeignKey('jobs.id'))
    role = Column(String(100), nullable=False)
    state = Column(String(24), nullable=False)
    plan = Column(JSON, nullable=False)
    cursor = Column(Integer, nullable=False, default=0)
    followups = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=now, nullable=False)
    expires_at = Column(DateTime, nullable=False)

class Answer(Base):
    __tablename__ = "interview_answers"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('interview_sessions.id'), index=True, nullable=False)
    position = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    turn = Column(Integer, nullable=False)
    transcript = Column(Text, nullable=False)
    transcript_confirmed = Column(Boolean, nullable=False, default=True)
    evaluation = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=now, nullable=False)
    __table_args__ = (UniqueConstraint('session_id','position','turn'),)

class Report(Base):
    __tablename__ = "interview_reports"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('interview_sessions.id'), unique=True, nullable=False)
    report = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=now, nullable=False)
