"""Database engine, session factory and base model setup using SQLAlchemy 2."""

import logging
import os
import sys
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

db_url = settings.DATABASE_URL


def _is_dir_writable(path: str = ".") -> bool:
    """Check if the given directory is writable."""
    try:
        test_file = os.path.join(path, ".probe_write_perm.tmp")
        with open(test_file, "w") as f:
            f.write("probe")
        os.remove(test_file)
        return True
    except Exception:
        return False


# In serverless runtimes (Vercel, AWS Lambda, Linux containers with read-only roots),
# relative sqlite URLs (e.g. sqlite:///./floodsaathi.db) fail. Redirect them to /tmp.
if db_url.startswith("sqlite:///."):
    if (
        not _is_dir_writable(".")
        or os.getenv("VERCEL")
        or os.getenv("VERCEL_ENV")
        or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
        or sys.platform != "win32"
    ):
        db_url = "sqlite:////tmp/floodsaathi.db"

connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}

try:
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=settings.DEBUG,
        future=True,
    )
    # Quick probe to ensure engine can connect and execute
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

# Enable SQLite foreign keys & DELETE journal mode (WAL requires shared-memory files that fail in /tmp on lambda)
if "sqlite" in db_url:

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=DELETE")
        except Exception:
            pass
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
        logger.info("Database schema verified and seeded successfully in %s", db_url)
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
