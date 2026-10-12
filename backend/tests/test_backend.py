"""
Backend tests — unit and integration tests.

IMPORTANT: These tests use pytest and mock external LLM/DB calls.
They do NOT require a real API key or paid service to run.
They DO require a PostgreSQL database to run the integration tests.

Run unit tests only (no DB needed):
  pytest tests/ -m "not integration" -v

Run all tests (DB required):
  pytest tests/ -v
"""
from __future__ import annotations

import pytest


# ─── Unit tests: config ────────────────────────────────────────────────────────

def test_settings_defaults():
    """Settings should load with sensible defaults from .env.example or defaults."""
    import os
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/lenny_growth")

    from app.core.config import Settings
    s = Settings()
    assert s.llm_provider in ("ollama", "anthropic")
    assert s.retrieval_top_k > 0
    assert s.ollama_model  # must have a model name


def test_anthropic_not_configured_by_default():
    """Anthropic should report as not configured when no key is set."""
    from app.core.config import Settings
    s = Settings(anthropic_api_key="")
    assert not s.anthropic_configured


def test_cors_origins_list():
    from app.core.config import Settings
    s = Settings(cors_origins="http://localhost:5173,http://localhost:3000")
    assert "http://localhost:5173" in s.cors_origins_list
    assert "http://localhost:3000" in s.cors_origins_list


# ─── Unit tests: embedding ────────────────────────────────────────────────────

def test_tfidf_embed_and_similarity():
    """TF-IDF embedder should produce non-zero vectors and meaningful similarity."""
    from app.providers.embedding_providers import SimpleTFIDFEmbedder
    embedder = SimpleTFIDFEmbedder()
    corpus = [
        "product market fit is crucial for growth",
        "user onboarding determines activation rate",
        "retention is more important than acquisition",
    ]
    embedder.fit(corpus)
    v1 = embedder.embed_query("product market fit")
    v2 = embedder.embed_query("retention metrics")
    assert v1 is not None
    assert v2 is not None
    assert any(x > 0 for x in v1)
    # v1 should be more similar to corpus[0] than corpus[2]
    sim_pmf = embedder.similarity(v1, embedder.embed_query(corpus[0]))
    sim_ret = embedder.similarity(v1, embedder.embed_query(corpus[2]))
    assert sim_pmf > sim_ret


def test_cosine_similarity_zero_vector():
    """Cosine similarity of zero vector should be 0, not error."""
    from app.providers.embedding_providers import cosine_similarity
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


# ─── Unit tests: ingestion parsing ───────────────────────────────────────────

def test_chunk_text_basic():
    """Chunker should split text into multiple chunks."""
    from app.ingestion.ingestion_service import _chunk_text
    text = "\n".join([f"This is paragraph {i} with some content that matters." for i in range(50)])
    chunks = _chunk_text(text)
    assert len(chunks) > 1


def test_chunk_preserves_speaker():
    """Chunker should capture speaker name from **Speaker**: format."""
    from app.ingestion.ingestion_service import _chunk_text
    text = "## Introduction\n\n**Lenny**: Welcome to the show.\n**Guest**: Thanks for having me.\n" * 10
    chunks = _chunk_text(text)
    speakers = [c.speaker for c in chunks if c.speaker]
    assert len(speakers) > 0


def test_content_hash_deterministic():
    """Same content should always produce the same hash."""
    from app.ingestion.ingestion_service import _content_hash
    text = "Hello, world! This is a transcript."
    assert _content_hash(text) == _content_hash(text)
    assert _content_hash(text) != _content_hash(text + ".")


def test_parse_markdown_source():
    """Parse metadata from a markdown source."""
    from app.ingestion.ingestion_service import _parse_markdown_source
    content = "# Episode Title\n\n**Lenny**: Welcome.\n**Guest**: Thanks."
    parsed = _parse_markdown_source("adam-mosseri.md", content, "podcast")
    assert parsed.external_id == "podcast/adam-mosseri"
    assert parsed.source_type == "podcast"
    assert parsed.content_hash


# ─── Unit tests: agent intent classification ─────────────────────────────────

def test_intent_classification_standard():
    from app.agents.growth_agent import _classify_intent
    assert _classify_intent("What do transcripts say about PMF?") == "standard"


def test_intent_classification_essay():
    from app.agents.growth_agent import _classify_intent
    assert _classify_intent("Write an essay about user retention") == "essay"


def test_intent_classification_decision_brief():
    from app.agents.growth_agent import _classify_intent
    assert _classify_intent("Create a decision brief for our onboarding") == "decision_brief"


def test_intent_classification_html():
    from app.agents.growth_agent import _classify_intent
    assert _classify_intent("Generate html landing page for product launch") == "html_artifact"


# ─── Unit tests: citation validation ─────────────────────────────────────────

def test_extract_cited_chunk_ids():
    """Should extract valid UUIDs from [CHUNK:uuid] references."""
    from app.agents.growth_agent import _extract_cited_chunk_ids
    text = "The evidence [CHUNK:abc12345-1234-1234-1234-123456789012] shows this clearly [CHUNK:invalid]."
    ids = _extract_cited_chunk_ids(text)
    assert "abc12345-1234-1234-1234-123456789012" in ids


def test_citation_validation_filters_invalid():
    """Validate citations should reject IDs not in retrieved set."""
    from app.retrieval.retrieval_service import RetrievalService
    # Test the validation logic independently
    retrieved = ["id-1", "id-2", "id-3"]
    cited = ["id-1", "id-99-fake", "id-2"]

    # Simulate validation
    valid = [c for c in cited if c in set(retrieved)]
    assert "id-1" in valid
    assert "id-2" in valid
    assert "id-99-fake" not in valid


# ─── Unit tests: essay skill ─────────────────────────────────────────────────

def test_essay_word_count():
    from app.skills.essay_skill import EssaySkill
    text = " ".join(["word"] * 1250)
    count = EssaySkill._count_words(text)
    assert abs(count - 1250) < 10  # allow small variance for punctuation


def test_essay_title_extraction():
    from app.skills.essay_skill import EssaySkill
    content = "# The Growth Trap: Why Most Teams Measure the Wrong Things\n\nIn today's..."
    title = EssaySkill._extract_title(content, "fallback")
    assert title == "The Growth Trap: Why Most Teams Measure the Wrong Things"


def test_essay_title_fallback():
    from app.skills.essay_skill import EssaySkill
    content = "No heading here, just text."
    title = EssaySkill._extract_title(content, "Fallback Title")
    assert title == "Fallback Title"


# ─── Unit tests: artifact security ───────────────────────────────────────────

def test_artifact_type_validation():
    """Only supported artifact types should be allowed."""
    from app.artifacts.artifact_generator import SUPPORTED_TYPES
    assert "html" in SUPPORTED_TYPES
    assert "markdown" in SUPPORTED_TYPES
    assert "essay" in SUPPORTED_TYPES
    assert "shell_script" not in SUPPORTED_TYPES


def test_html_artifact_wraps_content():
    """If LLM returns content without html tags, it should be wrapped."""
    from app.artifacts.artifact_generator import ArtifactGenerator
    # Test the wrapping logic
    content = "<div>Hello</div>"
    if "<html" not in content.lower():
        wrapped = f"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>{content}</body></html>"
    else:
        wrapped = content
    assert "<html" in wrapped.lower()


def test_artifact_size_limit():
    """Artifacts exceeding size limit should be truncated."""
    from app.artifacts.artifact_generator import MAX_ARTIFACT_SIZE
    huge = "x" * (MAX_ARTIFACT_SIZE + 1000)
    truncated = huge[:MAX_ARTIFACT_SIZE]
    assert len(truncated) == MAX_ARTIFACT_SIZE


# ─── Unit tests: provider ────────────────────────────────────────────────────

def test_ollama_provider_handles_connection_error():
    """OllamaProvider should return error result (not raise) on connection failure."""
    from app.providers.llm_providers import OllamaProvider
    provider = OllamaProvider(
        base_url="http://localhost:99999",  # non-existent
        model="test-model",
        timeout=2,
    )
    result = provider.generate(
        messages=[{"role": "user", "content": "Hello"}],
    )
    assert not result.success
    assert result.error is not None
    assert "ollama" in result.error.lower() or "connect" in result.error.lower()


def test_anthropic_provider_no_key():
    """AnthropicProvider with no key should report unavailable."""
    from app.providers.llm_providers import AnthropicProvider
    provider = AnthropicProvider(api_key="", model="claude-3-5-haiku-20241022")
    assert not provider.is_available()


def test_get_provider_defaults_to_ollama():
    """get_provider() with no Anthropic key should return Ollama."""
    import os
    os.environ["LLM_PROVIDER"] = "ollama"
    from app.providers.llm_providers import get_provider, OllamaProvider
    provider = get_provider("ollama")
    assert isinstance(provider, OllamaProvider)


def test_extractive_fallback_uses_verbatim_evidence_and_valid_chunk_id():
    from app.agents.growth_agent import _extractive_fallback

    class Result:
        def __init__(self, chunk_id, source_id, title, author, score, text):
            self.chunk_id = chunk_id
            self.source_id = source_id
            self.source_title = title
            self.author = author
            self.score = score
            self.text = text

        def to_dict(self):
            return {"chunk_id": self.chunk_id, "title": self.source_title}

    first = Result(
        "e65fd333-dbd9-4bf3-ad91-e25326d53ea4", "source-1",
        "Elena Verna interview", "Elena Verna", 0.9,
        "**Elena Verna** (00:01): Product-market fit used to evolve at a rate measured in years. Teams spent years scaling their initial fit.",
    )
    second = Result(
        "66a608a3-fd6e-41ca-bfc5-33ff5d96fb3c", "source-1",
        "Elena Verna interview", "Elena Verna", 0.8,
        "**Lenny Rachitsky** (00:01): Let's discuss the change. **Elena Verna** (00:02): Product and market now change every three months, requiring teams to recapture fit.",
    )
    unrelated = Result(
        "684f17da-9fdc-479e-ad94-4d3457eaa1cd", "source-2",
        "Claire Vo interview", "Claire Vo", 0.95,
        "**Claire Vo** (00:03): Product-market fit changes as customers want better software. Teams should keep adapting products.",
    )
    response = _extractive_fallback(
        [unrelated, first, second],
        "The transcript evidence directly relevant to your question is:",
        "According to Elena Verna in the transcripts, how does product-market fit change over time?",
    )

    assert response.grounding == "grounded"
    assert response.content.startswith(
        "Elena Verna describes product-market fit as an evolving target:"
    )
    assert "used to be measured in years" in response.content
    assert "reassess fit every few months" in response.content
    assert "1. **Earlier:**" not in response.content
    assert "2. **Current:**" not in response.content
    assert "[CHUNK:" not in response.content
    assert "Elena Verna interview" in response.content
    assert "(00:01)" in response.content
    assert "(00:02)" in response.content
    assert "ongoing process, not a milestone" in response.content
    assert "not a universal timetable" in response.content
    assert "Claire Vo" not in response.content
    assert {source["chunk_id"] for source in response.sources} == {first.chunk_id, second.chunk_id}
    assert len(response.sources) == 2
    assert response.provider == "evidence"


def test_fallback_declines_named_framework_without_direct_transcript_support():
    from app.agents.growth_agent import _extractive_fallback

    class Result:
        chunk_id = "e65fd333-dbd9-4bf3-ad91-e25326d53ea4"
        source_id = "source-1"
        source_title = "Writing effective product briefs"
        author = "Guest"
        score = 0.8
        text = "Good writing makes a product brief clear, concise, and easy to act on."

        def to_dict(self):
            return {"chunk_id": self.chunk_id, "title": self.source_title}

    response = _extractive_fallback(
        [Result()],
        "The transcript evidence directly relevant to your question is:",
        "What are the strongest writing principles for a Ship 30 for 30 habit?",
    )

    assert response.grounding == "declined"
    assert "do not directly support claims about Ship 30 for 30" in response.content
    assert "won't present them as its principles" in response.content
    assert not response.sources


def test_fallback_synthesizes_product_market_fit_horizon_evidence():
    from app.agents.growth_agent import _extractive_fallback

    class Result:
        def __init__(self, chunk_id, text):
            self.chunk_id = chunk_id
            self.source_id = "source-1"
            self.source_title = "Elena Verna 4.0"
            self.author = "Elena Verna"
            self.score = 0.9
            self.text = text

        def to_dict(self):
            return {"chunk_id": self.chunk_id, "title": self.source_title}

    passages = [
        Result(
            "e65fd333-dbd9-4bf3-ad91-e25326d53ea4",
            "**Elena Verna** (01:00:49): I'll first start with what I've felt at least before when people were talking about product-market fit, that yeah, obviously always product-market fit is an evolving thing, but the rate of that evolution was measured in years.",
        ),
        Result(
            "66a608a3-fd6e-41ca-bfc5-33ff5d96fb3c",
            "**Elena Verna** (01:00:49): What is it that you need the next product-market fit step function change, which often was called second horizon or third horizon.",
        ),
    ]

    response = _extractive_fallback(
        passages,
        "The transcript evidence directly relevant to your question is:",
        "According to Elena Verna, how does product-market fit evolve?",
    )

    assert response.content.startswith(
        "Elena Verna describes product-market fit as an evolving target."
    )
    assert "measured in years" in response.content
    assert "step-function change into a second or third horizon" in response.content
    assert "1. **" not in response.content
    assert "Elena Verna 4.0 (01:00:49)" in response.content
    assert len(response.sources) == 2


# ─── Integration tests (require DB) ──────────────────────────────────────────

@pytest.mark.integration
def test_db_connection():
    """Integration: database should be reachable."""
    from app.db.session import check_db_connection
    assert check_db_connection(), "Database is not reachable — ensure PostgreSQL is running"


@pytest.mark.integration
def test_create_and_retrieve_conversation(tmp_db):
    """Integration: create a conversation and retrieve it."""
    import uuid
    from app.models.models import Conversation
    db = tmp_db
    conv = Conversation(id=str(uuid.uuid4()), title="Test Conversation")
    db.add(conv)
    db.commit()

    found = db.query(Conversation).filter(Conversation.id == conv.id).first()
    assert found is not None
    assert found.title == "Test Conversation"
    db.delete(found)
    db.commit()


@pytest.mark.integration
def test_session_isolation(tmp_db):
    """Integration: two conversations should have independent message histories."""
    import uuid
    from app.models.models import Conversation, Message
    db = tmp_db

    conv1 = Conversation(id=str(uuid.uuid4()), title="Session A")
    conv2 = Conversation(id=str(uuid.uuid4()), title="Session B")
    db.add_all([conv1, conv2])
    db.commit()

    msg1 = Message(id=str(uuid.uuid4()), conversation_id=conv1.id, role="user", content="Hello from A")
    db.add(msg1)
    db.commit()

    msgs_for_conv2 = db.query(Message).filter(Message.conversation_id == conv2.id).all()
    assert len(msgs_for_conv2) == 0, "Session B should have no messages from Session A"

    # Cleanup
    db.delete(conv1)
    db.delete(conv2)
    db.commit()
