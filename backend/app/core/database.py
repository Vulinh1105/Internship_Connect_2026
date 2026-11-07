from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import DATABASE_URL, RUNTIME

class Base(DeclarativeBase):
    pass

RUNTIME.mkdir(parents=True, exist_ok=True)
options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    options["connect_args"] = {"check_same_thread": False, "timeout": 20}
engine = create_engine(DATABASE_URL, **options)
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")

Session = sessionmaker(engine, expire_on_commit=False, autoflush=True)

def get_db():
    with Session() as db:
        yield db
