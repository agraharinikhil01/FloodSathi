"""Database engine, session factory and base model setup using SQLAlchemy 2."""

import logging
import os
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

db_url = settings.DATABASE_URL
if (
    os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("LAMBDA_TASK_ROOT")
) and db_url.startswith("sqlite:///."):
    db_url = "sqlite:////tmp/floodsaathi.db"

connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}

try:
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=settings.DEBUG,
        future=True,
    )
    # Quick probe to ensure engine can connect and write
    with engine.connect() as test_conn:
        test_conn.execute(text("SELECT 1"))
except Exception as exc:
    logger.warning(
        "Primary DB connection (%s) failed (%s), switching to /tmp/floodsaathi.db", db_url, exc
    )
    db_url = "sqlite:////tmp/floodsaathi.db"
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG,
        future=True,
    )

# Enable SQLite foreign keys & WAL mode (with fallback if WAL fails in serverless /tmp)
if "sqlite" in db_url:

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
        except Exception:
            cursor.execute("PRAGMA journal_mode=DELETE")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()

_db_initialized = False


def ensure_db_initialized() -> None:
    """Ensure database schema is created and seeded with default data."""
    global _db_initialized
    if _db_initialized:
        return
    try:
        from backend.app.seed.seed_data import seed_database

        Base.metadata.create_all(bind=engine)
        seed_database()
        _db_initialized = True
    except Exception as exc:
        logger.warning("Automatic DB initialization/seed warning: %s", exc)


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session for FastAPI endpoints."""
    ensure_db_initialized()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
