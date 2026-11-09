from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from app.core.config import now
from app.core.database import Base

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True)
    name = Column(String(180), nullable=False)
    industry = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    details = Column(JSON, default=dict, nullable=False)

class Member(Base):
    __tablename__ = "company_members"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    manager = Column(Boolean, default=False, server_default="0", nullable=False)
    __table_args__ = (UniqueConstraint('company_id','user_id'),)

class CompanyRegistration(Base):
    __tablename__ = "company_registrations"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    tax_code = Column(String(13), unique=True, nullable=False)
    info = Column(JSON, nullable=False)
    files = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, index=True)
    reason = Column(Text, nullable=False, default="")


class Follow(Base):
    __tablename__ = "company_follows"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    __table_args__ = (UniqueConstraint('company_id','user_id'),)


class PlacementFeedback(Base):
    __tablename__ = "placement_feedback"
    application_id = Column(Integer, ForeignKey("applications.id"), primary_key=True)
    completed_at = Column(DateTime)
    interviewer_rating = Column(Integer)
    interviewer_note = Column(Text)
    student_rating = Column(Integer)
    student_review = Column(Text)
    review_status = Column(String(20))
