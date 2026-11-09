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
# Email (tùy chọn): để trống SMTP_HOST thì hệ thống không gửi email.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_SECURITY = os.getenv("SMTP_SECURITY", "starttls")
if SMTP_SECURITY not in {"starttls", "ssl", "none"}:
    raise ValueError("SMTP_SECURITY must be starttls, ssl or none")
MAIL_FROM = os.getenv("MAIL_FROM", "") or SMTP_USER
APP_LOCAL_PORT = os.getenv("APP_LOCAL_PORT", "8000")
APP_URL = os.getenv("APP_URL") or f"http://127.0.0.1:{APP_LOCAL_PORT}/app/"
try:
    LOCAL_TZ = ZoneInfo("Asia/Bangkok")
except ZoneInfoNotFoundError:
    LOCAL_TZ = timezone(timedelta(hours=7))

def now():
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)

def today():
    return now().date()
