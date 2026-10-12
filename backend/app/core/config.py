"""
Application configuration — loaded from environment variables / .env file.
All secrets must come from the environment; never hardcode them here.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the project root .env file — works regardless of CWD
# Walk up from this file's location to find the .env
_HERE = Path(__file__).resolve().parent          # app/core/
_BACKEND = _HERE.parent.parent                   # backend/
_PROJECT_ROOT = _BACKEND.parent                  # project root

def _find_env_file() -> str:
    """Find .env in project root, then backend dir, then CWD."""
    candidates = [
        _PROJECT_ROOT / ".env",
        _BACKEND / ".env",
        Path.cwd() / ".env",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return ".env"  # fallback


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    # Application
    app_env: str = "development"
    app_name: str = "Lenny Growth Assistant"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    # Database — defaults to SQLite so the app works without PostgreSQL
    database_url: str = f"sqlite:///{_PROJECT_ROOT / 'lenny_growth.db'}"

    # LLM Provider
    llm_provider: str = "ollama"  # "ollama" | "anthropic"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    # Embeddings
    embedding_provider: str = "simple"  # "ollama" | "simple"
    ollama_embedding_model: str = "nomic-embed-text"

    # Retrieval
    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.05
    max_context_tokens: int = 4000
    model_timeout_seconds: int = 90

    # Transcript source
    transcript_repo_url: str = "https://github.com/LennysNewsletter/lennys-newsletterpodcastdata"
    transcript_repo_api: str = "https://api.github.com/repos/LennysNewsletter/lennys-newsletterpodcastdata"

    # Logging
    log_level: str = "INFO"

    # Security
    secret_key: str = "change-me-in-production"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_api_key and self.anthropic_api_key.strip())

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in ("development", "dev")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
