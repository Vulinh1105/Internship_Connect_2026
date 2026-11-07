from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from app.core.config import now
from app.core.database import Base

class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True)
    application_id = Column(Integer, ForeignKey('applications.id'), index=True, nullable=False)
    invited_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    location = Column(String(255), nullable=False)
    note = Column(Text, default='', nullable=False)
    status = Column(String(24), default='invited', nullable=False)
    response = Column(Text)
    invited_at = Column(DateTime, default=now, nullable=False)
    cancelled_at = Column(DateTime)
