from sqlalchemy import Column, DateTime, Integer, String, Text
from app.core.config import now
from app.core.database import Base

class SyncTask(Base):
    __tablename__ = "vector_sync_queue"
    id = Column(Integer, primary_key=True)
    entity_type = Column(String(24), nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(String(16), nullable=False, default="refresh")
    status = Column(String(16), index=True, nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text)
    available_at = Column(DateTime, default=now, nullable=False)
    created_at = Column(DateTime, default=now, nullable=False)
