import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
RUNTIME = ROOT / "data/runtime"
UPLOADS = Path(os.getenv("UPLOADS_PATH") or ROOT / "data/uploads")
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{(RUNTIME / 'careerconnect.sqlite').as_posix()}"
QDRANT_URL = os.getenv("QDRANT_URL") or None
QDRANT_PATH = os.getenv("QDRANT_PATH") or str(RUNTIME / "qdrant")
AI_BACKEND = os.getenv("AI_BACKEND", "local")
if AI_BACKEND not in {"local", "openai"}:
    raise ValueError("AI_BACKEND must be local or openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DAILY_CALLS = max(1, int(os.getenv("AI_DAILY_CALLS", "100")))
DAILY_MOCKS = max(1, int(os.getenv("AI_DAILY_MOCKS", "5")))
try:
    LOCAL_TZ = ZoneInfo("Asia/Bangkok")
except ZoneInfoNotFoundError:
    LOCAL_TZ = timezone(timedelta(hours=7))

def now():
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)

def today():
    return now().date()
