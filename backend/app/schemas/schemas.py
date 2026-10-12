"""Pydantic schemas for API request/response validation."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ─── Conversations ──────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationList(BaseModel):
    items: List[ConversationOut]
    total: int
    page: int
    page_size: int


# ─── Messages ────────────────────────────────────────────────────────────────

class SourceReference(BaseModel):
    chunk_id: str
    source_id: str
    title: str
    author: Optional[str] = None
    url: Optional[str] = None
    excerpt: str
    score: float
    score_label: str = "retrieval relevance score (not correctness probability)"
    section: Optional[str] = None
    supports: Optional[str] = None  # which part of answer this supports


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    provider: Optional[str] = None  # override provider for this request
    mode: Optional[str] = None  # "standard" | "decision_brief" | "essay" | "artifact"
    artifact_type: Optional[str] = None


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime
    model: Optional[str] = None
    provider: Optional[str] = None
    status: Optional[str] = None
    grounding: Optional[str] = None
    sources: Optional[List[SourceReference]] = None
    duration_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

    class Config:
        from_attributes = True


class MessageList(BaseModel):
    items: List[MessageOut]
    total: int
    page: int
    page_size: int


# ─── Sources ─────────────────────────────────────────────────────────────────

class SourceOut(BaseModel):
    id: str
    source_type: str
    title: str
    author: Optional[str] = None
    canonical_url: Optional[str] = None
    external_id: Optional[str] = None
    ingested_at: datetime
    word_count: Optional[int] = None
    date_published: Optional[str] = None
    chunk_count: int = 0

    class Config:
        from_attributes = True


class SourceList(BaseModel):
    items: List[SourceOut]
    total: int
    page: int
    page_size: int


# ─── Ingestion ───────────────────────────────────────────────────────────────

class IngestionJobCreate(BaseModel):
    source_url: Optional[str] = None  # optional override


class IngestionJobOut(BaseModel):
    id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_files: Optional[int] = None
    processed_files: Optional[int] = None
    failed_files: Optional[int] = None
    sources_created: Optional[int] = None
    chunks_created: Optional[int] = None
    errors: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


# ─── Artifacts ───────────────────────────────────────────────────────────────

class ArtifactCreate(BaseModel):
    conversation_id: str
    artifact_type: str = Field(..., pattern="^(markdown|html|essay|decision_brief|experiment_card)$")
    title: Optional[str] = None
    prompt: Optional[str] = None


class ArtifactUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None


class ArtifactOut(BaseModel):
    id: str
    conversation_id: str
    artifact_type: str
    title: str
    content: str
    content_format: str
    source_references: Optional[List[Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Essay skill ─────────────────────────────────────────────────────────────

class EssayRequest(BaseModel):
    conversation_id: str
    audience: Optional[str] = "product managers and growth practitioners"
    thesis: Optional[str] = None
    tone: Optional[str] = "conversational, evidence-backed"
    title_preference: Optional[str] = None


# ─── Decision Brief ──────────────────────────────────────────────────────────

class DecisionBriefRequest(BaseModel):
    conversation_id: str
    question: str = Field(..., min_length=5)


# ─── Health ──────────────────────────────────────────────────────────────────

class HealthOut(BaseModel):
    status: str
    timestamp: datetime
    database: str
    llm_provider: str
    ollama_available: bool
    anthropic_configured: bool
    sources_indexed: int
    chunks_indexed: int


# ─── Models list ─────────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    model_config = {"protected_namespaces": ()}
    provider: str
    model_id: str
    display_name: str
    available: bool
    is_active: bool


class ModelsOut(BaseModel):
    active_provider: str
    active_model: str
    models: List[ModelInfo]


# ─── Errors ──────────────────────────────────────────────────────────────────

class ErrorOut(BaseModel):
    error_code: str
    message: str
    detail: Optional[str] = None
