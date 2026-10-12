"""SQLAlchemy database engine and session factory — lazy initialization.

Supports both PostgreSQL (production) and SQLite (development/testing).
SQLite is used automatically if DATABASE_URL starts with 'sqlite'.
This allows running the app without a PostgreSQL installation.
"""
from __future__ import annotations

from typing import Generator, Optional

from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    pass


# ─── Lazy engine creation ─────────────────────────────────────────────────────
# Engine is created on first use, not at module import time.
# This allows tests to import models without a live database.

_engine: Optional[Engine] = None
_SessionLocal_factory: Optional[sessionmaker] = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.database_url

        if db_url.startswith("sqlite"):
            # SQLite: enable WAL mode and foreign keys
            _engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                echo=False,
            )

            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # PostgreSQL (production)
            _engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                echo=False,
            )

    return _engine


def _get_session_local() -> sessionmaker:
    global _SessionLocal_factory
    if _SessionLocal_factory is None:
        _SessionLocal_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_get_engine(),
        )
    return _SessionLocal_factory


class SessionLocal:
    """Proxy so `SessionLocal()` works for background threads."""
    def __new__(cls, *args, **kwargs):
        factory = _get_session_local()
        return factory(*args, **kwargs)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a DB session and always closes it."""
    factory = _get_session_local()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database connection check failed: %s", exc)
        return False


def create_all_tables() -> None:
    """Create all tables defined in metadata (used for SQLite dev mode)."""
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("All tables created (create_all).")
