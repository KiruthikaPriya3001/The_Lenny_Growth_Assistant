"""Pytest configuration and fixtures."""
import os
import pytest

# Set test environment variables before imports
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/lenny_growth")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("ANTHROPIC_API_KEY", "")


@pytest.fixture
def tmp_db():
    """Integration fixture: provides a real DB session (requires PostgreSQL)."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
