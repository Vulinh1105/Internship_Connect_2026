from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from app.core.config import now
from app.core.database import Base

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True)
    student_id = Column(Integer, ForeignKey('students.id'), index=True, nullable=False)
    job_id = Column(Integer, ForeignKey('jobs.id'), index=True, nullable=False)
    cv_id = Column(Integer, ForeignKey('cvs.id'))
    cover_letter = Column(Text, nullable=False, default='')
    status = Column(String(24), nullable=False, default='pending')
    match_score = Column(Float)
    match_reason = Column(JSON)
    submitted_at = Column(DateTime, default=now, nullable=False)
    decision_at = Column(DateTime)
    decision_reason = Column(Text)
    __table_args__ = (UniqueConstraint('student_id','job_id'),)

class ApplicationEvent(Base):
    __tablename__ = "application_events"
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('applications.id'), index=True, nullable=False)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    before = Column(String(24))
    after = Column(String(24), nullable=False)
    occurred_at = Column(DateTime, default=now, nullable=False)
