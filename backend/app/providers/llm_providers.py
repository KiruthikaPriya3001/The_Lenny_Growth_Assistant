"""
Model provider abstraction layer.

Architecture:
  - BaseProvider: protocol/interface all providers implement
  - OllamaProvider: local Ollama via REST API
  - AnthropicProvider: cloud Anthropic Claude via SDK
  - DemoProvider: zero-dependency template engine (no external API)
  - ProviderFactory: selects provider based on settings + availability

The agent service uses these providers; it does not call any LLM directly.
Anthropic's Python SDK is used for the Anthropic provider (genuine integration).
Ollama's REST API is used for the local provider (no extra SDK needed).
DemoProvider synthesises answers directly from retrieved evidence text.
"""
from __future__ import annotations

import re
import textwrap
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_settings = get_settings()


# ─── Base ────────────────────────────────────────────────────────────────────

class GenerationResult:
    def __init__(
        self,
        content: str,
        model: str,
        provider: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
    ):
        self.content = content
        self.model = model
        self.provider = provider
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.duration_ms = duration_ms
        self.error = error
        self.success = error is None


class BaseProvider(ABC):
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> GenerationResult:
        """Synchronous generation — returns a GenerationResult."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is reachable/configured."""

    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier string."""

    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""


# ─── Demo provider ────────────────────────────────────────────────────────────

class DemoProvider(BaseProvider):
    """
    Zero-dependency demo provider — no Ollama, no API key required.

    Synthesises structured answers directly from retrieved transcript evidence
    that is embedded in the system prompt. Useful for:
      - Testing the full app flow without an external LLM
      - Demonstrating retrieval quality
      - CI/CD environments with no API access

    Limitations: answers are template-driven, not free-form language model
    output. Quality is bounded by the retrieved evidence quality.
    """

    _DEMO_NOTICE = (
        "\n\n---\n"
        "⚠️ **Demo Mode** — No LLM provider is configured. "
        "This answer was assembled directly from retrieved transcript evidence "
        "without AI language generation.\n"
        "To enable full AI responses: set `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` in `.env`, "
        "or run `ollama serve` and set `LLM_PROVIDER=ollama`."
    )

    def provider_name(self) -> str:
        return "demo"

    def model_name(self) -> str:
        return "demo-retrieval-v1"

    def is_available(self) -> bool:
        return True  # always available

    def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> GenerationResult:
        start = time.monotonic()

        # Extract the user's last question
        user_q = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_q = m.get("content", "")
                break

        # Parse evidence blocks from the system prompt
        evidence_excerpts = self._parse_evidence(system or "")

        content = self._synthesise(user_q, evidence_excerpts)
        elapsed = int((time.monotonic() - start) * 1000)

        return GenerationResult(
            content=content,
            model=self.model_name(),
            provider=self.provider_name(),
            input_tokens=len((system or "") + user_q) // 4,
            output_tokens=len(content) // 4,
            duration_ms=elapsed,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _parse_evidence(self, system: str) -> List[Dict[str, str]]:
        """Extract [CHUNK:id], SOURCE, SCORE, EXCERPT from system prompt."""
        blocks = []
        # Match each CHUNK block
        pattern = re.compile(
            r"\[CHUNK:([a-f0-9\-]{36})\]\s+SOURCE:\s*(.+?)\n"
            r"SCORE:\s*([\d.]+).*?\n"
            r"EXCERPT:\s*(.+?)(?=\n\n\[CHUNK:|\n---|\Z)",
            re.DOTALL,
        )
        for m in pattern.finditer(system):
            blocks.append({
                "chunk_id": m.group(1),
                "source": m.group(2).strip(),
                "score": float(m.group(3)),
                "excerpt": m.group(4).strip()[:400],
            })
        return sorted(blocks, key=lambda x: x["score"], reverse=True)

    def _synthesise(self, question: str, evidence: List[Dict]) -> str:
        if not evidence:
            return (
                f"**No transcript evidence found for:** *{question}*\n\n"
                "The knowledge base returned no relevant results for this query. "
                "This could mean:\n"
                "- Transcripts have not been ingested yet (go to **Knowledge Base → Ingest Transcripts**)\n"
                "- The question is outside the scope of indexed content\n"
                "- Try rephrasing with different keywords\n"
                + self._DEMO_NOTICE
            )

        # Detect brief/decision format request
        is_brief = any(w in question.lower() for w in ["brief", "decision", "experiment"])
        is_essay = any(w in question.lower() for w in ["essay", "write", "1250"])

        if is_brief:
            return self._format_brief(question, evidence)
        elif is_essay:
            return self._format_essay(question, evidence)
        else:
            return self._format_answer(question, evidence)

    def _format_answer(self, question: str, evidence: List[Dict]) -> str:
        lines = [f"## Answer: {question[:80]}\n"]

        lines.append(
            "Based on the retrieved transcript evidence, here is what the source material says:\n"
        )

        for i, e in enumerate(evidence[:4], 1):
            lines.append(f"**{i}. From: {e['source']}**")
            lines.append(f"> {e['excerpt']}\n")

        lines.append("\n### Key Takeaways\n")
        lines.append(
            "The evidence above represents the most relevant passages from Lenny's "
            "podcast and newsletter transcripts matching your query. "
            "Review each excerpt for context-specific recommendations.\n"
        )

        lines.append(self._DEMO_NOTICE)
        return "\n".join(lines)

    def _format_brief(self, question: str, evidence: List[Dict]) -> str:
        lines = ["## Growth Decision Brief\n"]
        lines.append(f"**1. Business Question**\n{question}\n")
        lines.append("**2. What the Source Material Says**\n")
        for e in evidence[:3]:
            lines.append(f"- *{e['source']}*: {e['excerpt'][:200]}\n")
        lines.append(
            "**3. Evidence-Backed Recommendation**\n"
            "Based on the retrieved evidence, consider the approaches described in the sources above. "
            "*(Hypothesis — configure an LLM provider for a full AI-generated recommendation)*\n"
        )
        lines.append(
            "**4. Suggested Experiment**\n"
            "Run a controlled experiment based on the transcript insights above. "
            "Measure impact after 2 weeks.\n"
        )
        lines.append("**5. Success Metric**\nDefine a measurable KPI aligned to your current growth lever.\n")
        lines.append("**6. Risks and Assumptions**\nContext may differ; validate with your own data.\n")
        lines.append(self._DEMO_NOTICE)
        return "\n".join(lines)

    def _format_essay(self, question: str, evidence: List[Dict]) -> str:
        lines = [f"# {question[:80]}\n"]
        lines.append(
            "**Hook:** What do the world's best growth practitioners actually say "
            f"about {question.lower()[:60]}? The transcripts reveal a clear pattern.\n"
        )
        lines.append("**Evidence from Lenny's transcripts:**\n")
        for e in evidence[:5]:
            lines.append(f"**{e['source']}** offers this insight:\n> {e['excerpt'][:300]}\n")
        lines.append(
            "\n**Takeaway:** The evidence points to a consistent theme across these conversations. "
            "Apply these lessons deliberately and measure the results.\n"
        )
        lines.append(self._DEMO_NOTICE)
        return "\n".join(lines)


# ─── Ollama ──────────────────────────────────────────────────────────────────

class OllamaProvider(BaseProvider):
    """Uses Ollama REST API for local LLM inference."""

    def __init__(self, base_url: str, model: str, timeout: int = 90):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def provider_name(self) -> str:
        return "ollama"

    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=5)
            if resp.status_code != 200:
                return False
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            # Check if our configured model is available (allow prefix match)
            return any(m.startswith(self._model.split(":")[0]) for m in models)
        except Exception as exc:
            logger.warning("Ollama availability check failed: %s", exc)
            return False

    def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> GenerationResult:
        start = time.monotonic()
        try:
            payload: Dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
            if system:
                payload["system"] = system

            resp = httpx.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            elapsed = int((time.monotonic() - start) * 1000)

            return GenerationResult(
                content=content,
                model=self._model,
                provider="ollama",
                input_tokens=data.get("prompt_eval_count"),
                output_tokens=data.get("eval_count"),
                duration_ms=elapsed,
            )
        except httpx.ConnectError:
            return GenerationResult(
                content="",
                model=self._model,
                provider="ollama",
                duration_ms=int((time.monotonic() - start) * 1000),
                error=(
                    f"Cannot connect to Ollama at {self._base_url}. "
                    "Ensure Ollama is running: `ollama serve`. "
                    f"Then pull the model: `ollama pull {self._model}`"
                ),
            )
        except httpx.TimeoutException:
            return GenerationResult(
                content="",
                model=self._model,
                provider="ollama",
                duration_ms=int((time.monotonic() - start) * 1000),
                error=f"Ollama request timed out after {self._timeout}s. Try a smaller model.",
            )
        except Exception as exc:
            logger.error("Ollama generation error: %s", exc)
            return GenerationResult(
                content="",
                model=self._model,
                provider="ollama",
                duration_ms=int((time.monotonic() - start) * 1000),
                error=f"Ollama error: {str(exc)[:200]}",
            )


# ─── Anthropic ───────────────────────────────────────────────────────────────

class AnthropicProvider(BaseProvider):
    """Uses the official Anthropic Python SDK for Claude generation."""

    def __init__(self, api_key: str, model: str, timeout: int = 90):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=self._api_key,
                    timeout=float(self._timeout),
                )
            except ImportError:
                raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    def provider_name(self) -> str:
        return "anthropic"

    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> GenerationResult:
        if not self.is_available():
            return GenerationResult(
                content="",
                model=self._model,
                provider="anthropic",
                error="Anthropic API key is not configured. Set ANTHROPIC_API_KEY in .env.",
            )
        start = time.monotonic()
        try:
            client = self._get_client()
            kwargs: Dict[str, Any] = {
                "model": self._model,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system

            response = client.messages.create(**kwargs)
            content = response.content[0].text if response.content else ""
            elapsed = int((time.monotonic() - start) * 1000)

            return GenerationResult(
                content=content,
                model=self._model,
                provider="anthropic",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                duration_ms=elapsed,
            )
        except Exception as exc:
            error_msg = str(exc)
            # Never expose the actual key in error messages
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                error_msg = "Anthropic authentication failed. Check your ANTHROPIC_API_KEY."
            logger.error("Anthropic generation error: %s", error_msg[:200])
            return GenerationResult(
                content="",
                model=self._model,
                provider="anthropic",
                duration_ms=int((time.monotonic() - start) * 1000),
                error=error_msg[:300],
            )


# ─── Factory ─────────────────────────────────────────────────────────────────

def get_provider(provider_name: Optional[str] = None) -> BaseProvider:
    """
    Return a configured provider instance based on settings and availability.

    Priority order:
      1. Explicitly requested provider instance (even when temporarily unavailable)
      2. Configured LLM_PROVIDER in settings (if available)
      3. Anthropic (if API key is set)
      4. Ollama (if running)
      5. DemoProvider (always available fallback)

    The key behavior is that callers can inspect the provider type they asked for,
    while each provider's own `generate()` method reports connection/config errors
    gracefully instead of silently swapping to DemoProvider.
    """
    s = _settings
    name = (provider_name or s.llm_provider).lower()

    if name == "anthropic":
        provider = AnthropicProvider(
            api_key=s.anthropic_api_key,
            model=s.anthropic_model,
            timeout=s.model_timeout_seconds,
        )
        if provider.is_available():
            return provider
        logger.warning("Anthropic requested but ANTHROPIC_API_KEY not set — checking Ollama")
        name = "ollama"

    if name == "ollama":
        provider = OllamaProvider(
            base_url=s.ollama_base_url,
            model=s.ollama_model,
            timeout=s.model_timeout_seconds,
        )
        if provider.is_available():
            return provider
        logger.warning(
            "Ollama requested but not available at %s — returning OllamaProvider so callers "
            "can surface a proper connection error. Run `ollama serve` then `ollama pull %s` "
            "to enable local AI.",
            s.ollama_base_url, s.ollama_model,
        )
        return provider

    if name == "demo":
        return DemoProvider()

    # Final fallback: DemoProvider so the app always stays functional
    logger.warning(
        "No LLM provider available (provider=%s). Using DemoProvider. "
        "Configure ANTHROPIC_API_KEY or run Ollama to enable full AI responses.",
        name,
    )
    return DemoProvider()
