"""
Retrieval service — finds relevant transcript chunks for a user query.

Strategy:
  1. Embed the query (simple TF-IDF or Ollama neural)
  2. Score all stored chunks using cosine similarity
  3. Apply minimum score threshold
  4. Return top-K results with source metadata

When pgvector is not available (standard PostgreSQL), we load chunk embeddings
from the database and score in Python. For larger corpora, this should be
replaced with ANN search (pgvector, FAISS, etc.).

Retrieval scores are clearly labeled as retrieval relevance scores, NOT
correctness probabilities.
"""
from __future__ import annotations

import struct
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.models import Source, TranscriptChunk
from app.providers.embedding_providers import get_embedder

logger = get_logger(__name__)
_settings = get_settings()


def _bytes_to_vector(data: bytes) -> Optional[np.ndarray]:
    """Deserialize float32 bytes back to numpy array."""
    if not data:
        return None
    try:
        arr = np.frombuffer(data, dtype=np.float32)
        return arr
    except Exception:
        return None


class RetrievalResult:
    def __init__(
        self,
        chunk_id: str,
        source_id: str,
        source_title: str,
        source_type: str,
        author: Optional[str],
        canonical_url: Optional[str],
        text: str,
        score: float,
        chunk_index: int,
        section_heading: Optional[str],
        speaker: Optional[str],
        date_published: Optional[str],
    ):
        self.chunk_id = chunk_id
        self.source_id = source_id
        self.source_title = source_title
        self.source_type = source_type
        self.author = author
        self.canonical_url = canonical_url
        self.text = text
        self.score = round(score, 4)
        self.chunk_index = chunk_index
        self.section_heading = section_heading
        self.speaker = speaker
        self.date_published = date_published

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
            "title": self.source_title,
            "source_type": self.source_type,
            "author": self.author,
            "url": self.canonical_url,
            "excerpt": self.text[:600],
            "full_text": self.text,
            "score": self.score,
            "score_label": "retrieval relevance score (not correctness probability)",
            "chunk_index": self.chunk_index,
            "section": self.section_heading,
            "speaker": self.speaker,
            "date": self.date_published,
        }


class RetrievalService:
    """Retrieves relevant transcript chunks for a user query."""

    def __init__(self, db: Session):
        self.db = db
        self.embedder = get_embedder()

    def _full_text_search(self, query: str, limit: int = 20) -> List[Tuple[str, float]]:
        """
        Fallback full-text search using PostgreSQL LIKE for basic keyword matching.
        Returns list of (chunk_id, score) tuples.
        """
        keywords = [w.lower() for w in query.split() if len(w) > 3]
        if not keywords:
            return []

        # Simple keyword scoring without pgvector
        chunks = self.db.query(TranscriptChunk.id, TranscriptChunk.text).all()
        scored: List[Tuple[str, float]] = []
        for chunk_id, text in chunks:
            text_lower = text.lower()
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > 0:
                score = matches / len(keywords)
                scored.append((chunk_id, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
        source_type: Optional[str] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant chunks for a query.
        Returns results above min_score threshold, limited to top_k.
        """
        top_k = top_k or _settings.retrieval_top_k
        min_score = min_score if min_score is not None else _settings.retrieval_min_score

        try:
            query_vec = self.embedder.embed_query(query)
            if query_vec is None:
                logger.warning("Query embedding failed; falling back to keyword search")
                return self._keyword_retrieve(query, top_k, min_score, source_type)

            # Load all chunks with embeddings (for small corpora; use ANN for large ones)
            q = self.db.query(TranscriptChunk).filter(TranscriptChunk.embedding.isnot(None))
            if source_type:
                q = q.join(Source).filter(Source.source_type == source_type)
            chunks = q.all()

            if not chunks:
                logger.info("No embedded chunks found; using keyword search")
                return self._keyword_retrieve(query, top_k, min_score, source_type)

            query_arr = np.array(query_vec, dtype=np.float32)
            query_norm = np.linalg.norm(query_arr)

            scored: List[Tuple[float, TranscriptChunk]] = []
            for chunk in chunks:
                chunk_arr = _bytes_to_vector(chunk.embedding)
                if chunk_arr is None or len(chunk_arr) != len(query_arr):
                    continue
                chunk_norm = np.linalg.norm(chunk_arr)
                if query_norm == 0 or chunk_norm == 0:
                    continue
                sim = float(np.dot(query_arr, chunk_arr) / (query_norm * chunk_norm))
                if sim >= min_score:
                    scored.append((sim, chunk))

            scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[:top_k]

            results = []
            for score, chunk in top:
                source = self.db.query(Source).filter(Source.id == chunk.source_id).first()
                if not source:
                    continue
                results.append(RetrievalResult(
                    chunk_id=chunk.id,
                    source_id=source.id,
                    source_title=source.title,
                    source_type=source.source_type,
                    author=source.author,
                    canonical_url=source.canonical_url,
                    text=chunk.text,
                    score=score,
                    chunk_index=chunk.chunk_index,
                    section_heading=chunk.section_heading,
                    speaker=chunk.speaker,
                    date_published=source.date_published,
                ))

            logger.info("Retrieved %d results (query=%r)", len(results), query[:60])
            return results

        except Exception as exc:
            logger.error("Retrieval failed: %s", exc)
            return []

    def _keyword_retrieve(
        self,
        query: str,
        top_k: int,
        min_score: float,
        source_type: Optional[str],
    ) -> List[RetrievalResult]:
        """Keyword-based retrieval fallback (no embeddings needed)."""
        keywords = [w.lower() for w in query.split() if len(w) > 3]
        if not keywords:
            return []

        q = self.db.query(TranscriptChunk).join(Source)
        if source_type:
            q = q.filter(Source.source_type == source_type)
        chunks = q.limit(500).all()  # Score a sample of chunks

        scored: List[Tuple[float, TranscriptChunk]] = []
        for chunk in chunks:
            text_lower = chunk.text.lower()
            matches = sum(1 for kw in keywords if kw in text_lower)
            score = matches / max(len(keywords), 1)
            if score >= min_score:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        results = []
        for score, chunk in top:
            source = self.db.query(Source).filter(Source.id == chunk.source_id).first()
            if not source:
                continue
            results.append(RetrievalResult(
                chunk_id=chunk.id,
                source_id=source.id,
                source_title=source.title,
                source_type=source.source_type,
                author=source.author,
                canonical_url=source.canonical_url,
                text=chunk.text,
                score=score,
                chunk_index=chunk.chunk_index,
                section_heading=chunk.section_heading,
                speaker=chunk.speaker,
                date_published=source.date_published,
            ))
        return results

    def validate_citations(
        self,
        cited_ids: List[str],
        retrieved_ids: List[str],
    ) -> List[str]:
        """
        Return only citation IDs that appear in the retrieved set.
        Any ID not in retrieved_ids is rejected — never fabricated citations.
        """
        valid_set = set(retrieved_ids)
        return [cid for cid in cited_ids if cid in valid_set]
