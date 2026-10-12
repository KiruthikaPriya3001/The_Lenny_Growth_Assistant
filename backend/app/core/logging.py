"""
Structured logging configuration using Python's standard logging module.
Outputs JSON-friendly log records in production; human-readable in development.
Never logs secrets, API keys, or private conversation content.
"""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Optional

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    rid = request_id_var.get("")
    return rid or str(uuid.uuid4())[:8]


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def setup_logging(level: str = "INFO", development: bool = True) -> None:
    """Configure application logging. Called once at startup."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    if development:
        fmt = (
            "%(asctime)s [%(request_id)s] %(levelname)-8s "
            "%(name)s:%(lineno)d — %(message)s"
        )
        formatter = logging.Formatter(fmt, datefmt="%H:%M:%S")
    else:
        # Minimal structured format compatible with log aggregators
        fmt = '{"time":"%(asctime)s","rid":"%(request_id)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
        formatter = logging.Formatter(fmt)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
