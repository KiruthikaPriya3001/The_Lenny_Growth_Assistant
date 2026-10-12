"""Models API — list available LLM providers and models."""
from __future__ import annotations

from fastapi import APIRouter
from app.core.config import get_settings
from app.providers.llm_providers import OllamaProvider
from app.schemas.schemas import ModelInfo, ModelsOut

router = APIRouter()
_settings = get_settings()


@router.get("/models", response_model=ModelsOut)
def list_models():
    """List available model providers and their availability status."""
    # Check Ollama availability
    ollama_ok = False
    try:
        provider = OllamaProvider(_settings.ollama_base_url, _settings.ollama_model)
        ollama_ok = provider.is_available()
    except Exception:
        pass

    models = [
        ModelInfo(
            provider="ollama",
            model_id=_settings.ollama_model,
            display_name=f"Ollama ({_settings.ollama_model})",
            available=ollama_ok,
            is_active=_settings.llm_provider == "ollama",
        ),
        ModelInfo(
            provider="anthropic",
            model_id=_settings.anthropic_model,
            display_name=f"Claude ({_settings.anthropic_model})",
            available=_settings.anthropic_configured,
            is_active=_settings.llm_provider == "anthropic",
        ),
    ]

    return ModelsOut(
        active_provider=_settings.llm_provider,
        active_model=_settings.ollama_model if _settings.llm_provider == "ollama" else _settings.anthropic_model,
        models=models,
    )
