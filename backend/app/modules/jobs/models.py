from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from app.core.config import now
from app.core.database import Base

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True)
    company_id = Column(Integer, ForeignKey('companies.id'), index=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    location = Column(String(100), index=True, nullable=False)
    work_mode = Column(String(20), nullable=False)
    level = Column(String(24), nullable=False, default='intern')
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    deadline = Column(Date)
    status = Column(String(24), index=True, nullable=False, default='open')
    moderation_status = Column(String(24), index=True, nullable=False, default='pending')
    deleted_at = Column(DateTime)
    skills = Column(JSON, default=list, nullable=False)
    details = Column(JSON, default=dict, nullable=False)
    flags = Column(JSON, default=list, nullable=False)
    content_hash = Column(String(64))
    vector_synced_at = Column(DateTime)
    created_at = Column(DateTime, default=now, nullable=False)

class SavedJob(Base):
    __tablename__ = "saved_jobs"
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    __table_args__ = (UniqueConstraint('job_id','user_id'),)

class Review(Base):
    __tablename__ = "job_reviews"
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    reviewer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    decision = Column(String(24), nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now, nullable=False)
