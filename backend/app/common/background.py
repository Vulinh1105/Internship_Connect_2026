import logging
from app.core.database import Session

log = logging.getLogger(__name__)

def sync_pending():
    from app.ai.vector.sync import drain
    try:
        with Session() as db:
            drain(db, limit=20)
    except Exception:
        log.exception("Vector worker failed")
