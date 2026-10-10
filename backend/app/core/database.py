from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

connect_args = {}
engine_options = {
    "echo": False,
    # Detect stale connections before using them.
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    # Give SQLite a little time to wait if another request briefly holds a lock.
    connect_args["timeout"] = 30
    # Keep the existing SQLAlchemy pool sizing defaults; larger pools can make
    # SQLite contention worse and do not fix long-running queries.

engine_options["connect_args"] = connect_args
engine = create_engine(DATABASE_URL, **engine_options)

# Enable foreign keys for SQLite.
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
