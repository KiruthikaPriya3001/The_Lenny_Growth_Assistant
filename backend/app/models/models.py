"""
SQLAlchemy ORM models for all persistent entities.

Tables:
  conversations  — independent chat sessions
  messages       — per-session message history
  sources        — ingested transcript/newsletter sources
  transcript_chunks — chunked text with optional embeddings
  artifacts      — generated markdown/HTML artifacts
  ingestion_jobs — ingestion tracking
  evaluation_records — RAG evaluation runs
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False, default="New Conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    owner_id = Column(String(100), nullable=True)  # reserved for future auth
    meta = Column(JSON, nullable=True)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    artifacts = relationship("Artifact", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    model = Column(String(200), nullable=True)
    provider = Column(String(50), nullable=True)
    status = Column(String(20), nullable=True, default="ok")  # "ok" | "error" | "timeout"
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    grounding = Column(String(30), nullable=True)  # "grounded" | "partial" | "ungrounded" | "declined"
    sources_used = Column(JSON, nullable=True)  # list of source IDs cited
    retrieval_meta = Column(JSON, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")


class Source(Base):
    __tablename__ = "sources"

    id = Column(String(36), primary_key=True, default=_uuid)
    source_type = Column(String(30), nullable=False)  # "podcast" | "newsletter"
    title = Column(String(1000), nullable=False)
    author = Column(String(500), nullable=True)
    canonical_url = Column(String(2000), nullable=True)
    external_id = Column(String(500), nullable=True)  # e.g., filename slug
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    content_hash = Column(String(64), nullable=True)
    word_count = Column(Integer, nullable=True)
    date_published = Column(String(20), nullable=True)
    meta = Column(JSON, nullable=True)

    chunks = relationship("TranscriptChunk", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("external_id", name="uq_source_external_id"),)


class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"

    id = Column(String(36), primary_key=True, default=_uuid)
    source_id = Column(String(36), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    char_count = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    section_heading = Column(String(500), nullable=True)
    speaker = Column(String(200), nullable=True)
    start_char = Column(Integer, nullable=True)
    embedding = Column(LargeBinary, nullable=True)  # numpy float32 bytes
    embedding_model = Column(String(200), nullable=True)
    meta = Column(JSON, nullable=True)

    source = relationship("Source", back_populates="chunks")

    __table_args__ = (UniqueConstraint("source_id", "chunk_index", name="uq_chunk_source_index"),)


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(String(36), primary_key=True, default=_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    artifact_type = Column(String(50), nullable=False)  # "markdown" | "html" | "essay" | "decision_brief"
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    content_format = Column(String(20), nullable=False, default="markdown")
    source_references = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    meta = Column(JSON, nullable=True)

    conversation = relationship("Conversation", back_populates="artifacts")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String(36), primary_key=True, default=_uuid)
    status = Column(String(20), nullable=False, default="pending")  # pending|running|done|failed
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_files = Column(Integer, nullable=True)
    processed_files = Column(Integer, nullable=True, default=0)
    failed_files = Column(Integer, nullable=True, default=0)
    sources_created = Column(Integer, nullable=True, default=0)
    chunks_created = Column(Integer, nullable=True, default=0)
    errors = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)


class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id = Column(String(36), primary_key=True, default=_uuid)
    dataset_version = Column(String(50), nullable=True)
    test_case_id = Column(String(100), nullable=True)
    question = Column(Text, nullable=True)
    expected_answer = Column(Text, nullable=True)
    actual_answer = Column(Text, nullable=True)
    recall_at_k = Column(Float, nullable=True)
    citation_correct = Column(Integer, nullable=True)  # 0/1
    answer_relevant = Column(Float, nullable=True)
    abstained = Column(Integer, nullable=True)  # 0/1
    latency_ms = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    meta = Column(JSON, nullable=True)
