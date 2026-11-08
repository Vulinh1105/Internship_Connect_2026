from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, false
from app.core.config import now
from app.core.database import Base

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    code = Column(String(80), unique=True)
    student_code = Column(String(80), unique=True)
    name = Column(String(150), nullable=False)
    major = Column(String(150), default='', nullable=False)
    summary = Column(Text, default='', nullable=False)
    skills = Column(JSON, default=list, nullable=False)
    preferences = Column(JSON, default=dict, nullable=False)
    details = Column(JSON, default=dict, nullable=False)

class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True)
    code = Column(String(80), nullable=False, unique=True)
    name = Column(String(100), nullable=False, unique=True)

class CV(Base):
    __tablename__ = "cvs"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), index=True, nullable=False)
    original_name = Column(String(255), nullable=False)
    storage_key = Column(String(255), nullable=False)
    parsed_text = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    extracted = Column(JSON, nullable=False)
    confirmed = Column(Boolean, default=False, nullable=False)
    archived = Column(Boolean, server_default=false(), nullable=False)
    created_at = Column(DateTime, default=now, nullable=False)
    __table_args__ = (UniqueConstraint('student_id','content_hash'),)
