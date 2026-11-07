from contextlib import contextmanager
from datetime import datetime, time
from threading import Lock
from time import perf_counter
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func, select
from fastapi import HTTPException
from app.core.config import DAILY_CALLS, now, today
from app.core.database import Base, Session

class Usage(Base):
    __tablename__ = "ai_usage_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    feature = Column(String(40), nullable=False)
    model = Column(String(100), nullable=False)
    tokens_in = Column(Integer, nullable=False, default=0)
    tokens_out = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float)
    latency_ms = Column(Integer, nullable=False, default=0)
    status = Column(String(16), nullable=False)
    created_at = Column(DateTime, default=now, nullable=False)

_lock = Lock()

def check(db,user_id):
    if user_id is not None and db.scalar(select(func.count(Usage.id)).where(
        Usage.user_id==user_id,Usage.created_at>=datetime.combine(today(),time.min)))>=DAILY_CALLS:
        raise HTTPException(429,"Đã hết hạn mức AI hôm nay. Hạn mức đặt lại lúc 00:00 (UTC+7).")

@contextmanager
def call(user_id,feature,model):
    with _lock, Session() as db:
        check(db,user_id)
        entry=Usage(user_id=user_id,feature=feature,model=model,status="running")
        db.add(entry)
        db.commit()
        ident=entry.id
    t=perf_counter()
    stats={"tokens_in":0,"tokens_out":0,"cost_usd":None}
    status="failed"
    try:
        yield stats
        status="ok"
    finally:
        with Session() as db:
            entry=db.get(Usage,ident)
            entry.status=status
            entry.latency_ms=int((perf_counter()-t)*1000)
            for k,v in stats.items():
                setattr(entry,k,v)
            db.commit()
