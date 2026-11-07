from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from app.core.config import now
from app.core.database import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer,primary_key=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=False,index=True)
    summary = Column(Text,default="",nullable=False)
    created_at = Column(DateTime,default=now,nullable=False)

class Message(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer,primary_key=True)
    session_id = Column(Integer,ForeignKey("chat_sessions.id"),nullable=False,index=True)
    role = Column(String(16),nullable=False)
    text = Column(Text,nullable=False)
    meta = Column("metadata",JSON,default=dict,nullable=False)
    created_at = Column(DateTime,default=now,nullable=False)

class Feedback(Base):
    __tablename__ = "chat_feedback"
    id = Column(Integer,primary_key=True)
    message_id = Column(Integer,ForeignKey("chat_messages.id"),nullable=False,unique=True)
    rating = Column(Integer,nullable=False)
    comment = Column(Text,nullable=False,default="")
