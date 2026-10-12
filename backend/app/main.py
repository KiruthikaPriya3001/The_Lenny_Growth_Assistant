"""
FastAPI application entry point.

Features:
  - Structured logging setup
  - CORS configuration
  - API router registration
  - Health/readiness endpoints
  - Request ID middleware
  - Global exception handling (never exposes stack traces to clients)
  - Startup: DB connection check, migration check
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger, request_id_var, setup_logging

settings = get_settings()
setup_logging(level=settings.log_level, development=settings.is_development)
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Evidence-first growth workspace powered by Lenny's Podcast and Newsletter transcripts.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request ID middleware ────────────────────────────────────────────────────

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    token = request_id_var.set(rid)
    start = time.monotonic()
    try:
        response = await call_next(request)
        duration = int((time.monotonic() - start) * 1000)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Response-Time-Ms"] = str(duration)
        logger.info("%s %s %d %dms", request.method, request.url.path, response.status_code, duration)
        return response
    except Exception as exc:
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
            headers={"X-Request-ID": rid},
        )
    finally:
        request_id_var.reset(token)


# ─── Health endpoints ─────────────────────────────────────────────────────────

@app.get("/api/health", tags=["health"])
def health():
    """Liveness check — always returns 200 if application is running."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/ready", tags=["health"])
def readiness():
    """
    Readiness check — verifies database and optional model providers.
    Returns 200 with component statuses. Does NOT fail on missing cloud keys.
    """
    from app.db.session import check_db_connection
    from app.models.models import Source, TranscriptChunk
    from app.db.session import SessionLocal
    from app.providers.llm_providers import OllamaProvider

    db_ok = check_db_connection()

    # Check Ollama
    ollama_ok = False
    try:
        ollama = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
        ollama_ok = ollama.is_available()
    except Exception:
        pass

    # Source/chunk counts from DB
    sources_count = 0
    chunks_count = 0
    if db_ok:
        try:
            db = SessionLocal()
            sources_count = db.query(Source).count()
            chunks_count = db.query(TranscriptChunk).count()
            db.close()
        except Exception:
            pass

    status = "ready" if db_ok else "degraded"
    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "database": "ok" if db_ok else "unavailable",
        "llm_provider": settings.llm_provider,
        "ollama_available": ollama_ok,
        "anthropic_configured": settings.anthropic_configured,
        "sources_indexed": sources_count,
        "chunks_indexed": chunks_count,
    }


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info("Starting %s (env=%s)", settings.app_name, settings.app_env)

    # Import all models to ensure metadata is populated before create_all
    from app.models import models as _models  # noqa

    from app.db.session import check_db_connection, create_all_tables, _get_engine

    engine = _get_engine()
    is_sqlite = settings.is_sqlite

    if is_sqlite:
        # SQLite: auto-create all tables (no alembic needed)
        create_all_tables()
        logger.info("SQLite mode: all tables created at %s", settings.database_url)
    else:
        if not check_db_connection():
            logger.error(
                "Database not reachable at startup. URL host=%s. "
                "Ensure PostgreSQL is running and DATABASE_URL is correct.",
                settings.database_url.split("@")[-1] if "@" in settings.database_url else "configured",
            )
        else:
            logger.info("PostgreSQL connection: OK")



# ─── Include routers ─────────────────────────────────────────────────────────

from app.api import sessions, messages, sources, ingestion, artifacts, skills, models

app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(messages.router, prefix="/api", tags=["messages"])
app.include_router(sources.router, prefix="/api", tags=["sources"])
app.include_router(ingestion.router, prefix="/api", tags=["ingestion"])
app.include_router(artifacts.router, prefix="/api", tags=["artifacts"])
app.include_router(skills.router, prefix="/api", tags=["skills"])
app.include_router(models.router, prefix="/api", tags=["models"])
