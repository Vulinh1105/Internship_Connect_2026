from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from app.core.config import now
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
    kind = Column(String(60), nullable=False)
    message = Column(String(400), nullable=False)
    target_id = Column(Integer)
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=now, nullable=False)


class NotificationEmail(Base):
    __tablename__ = "notification_emails"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(String(400), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    available_at = Column(DateTime, default=now, nullable=False)
