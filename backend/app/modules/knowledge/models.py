from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from app.core.config import now
from app.core.database import Base

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True)
    title = Column(String(220), nullable=False)
    source = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    topic = Column(String(100), default='FAQ', nullable=False)
    version = Column(String(30), nullable=False, default='1')
    visibility = Column(String(20), default='public', nullable=False)
    status = Column(String(24), default='published', nullable=False)
    content_hash = Column(String(64))
    vector_synced_at = Column(DateTime)

class Chunk(Base):
    __tablename__ = "knowledge_chunks"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'), index=True, nullable=False)
    position = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    __table_args__ = (UniqueConstraint('document_id','position'),)
