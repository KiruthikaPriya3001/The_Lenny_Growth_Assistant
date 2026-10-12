"""
Transcript ingestion pipeline.

Workflow:
  1. Fetch file listing from LennysNewsletter GitHub repo
  2. Download each .md transcript
  3. Parse markdown frontmatter and content
  4. Chunk by paragraph/section boundaries
  5. Generate embeddings
  6. Persist sources and chunks to PostgreSQL (with duplicate detection)
  7. Report status

Source: https://github.com/LennysNewsletter/lennys-newsletterpodcastdata
Format: Markdown files with podcast transcripts and newsletters
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.models import IngestionJob, Source, TranscriptChunk
from app.providers.embedding_providers import BaseEmbedder, get_embedder, SimpleTFIDFEmbedder

logger = get_logger(__name__)
_settings = get_settings()

CHUNK_SIZE = 800      # characters per chunk (soft limit)
CHUNK_OVERLAP = 100   # overlap between chunks


@dataclass
class ParsedSource:
    external_id: str
    source_type: str
    title: str
    author: Optional[str]
    canonical_url: Optional[str]
    date_published: Optional[str]
    word_count: Optional[int]
    content: str
    content_hash: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedChunk:
    chunk_index: int
    text: str
    char_count: int
    section_heading: Optional[str]
    speaker: Optional[str]
    start_char: int


# ─── GitHub fetch helpers ─────────────────────────────────────────────────────

def _fetch_json(url: str, timeout: int = 30) -> Any:
    resp = httpx.get(url, timeout=timeout, headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()


def _fetch_text(url: str, timeout: int = 30) -> str:
    resp = httpx.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _fetch_index() -> List[Dict[str, Any]]:
    """Fetch the index.json with titles, dates, guests from the official repo."""
    url = f"https://raw.githubusercontent.com/LennysNewsletter/lennys-newsletterpodcastdata/main/index.json"
    try:
        data = _fetch_json(url)
        entries = []
        for p in data.get("podcasts", []):
            p["_type"] = "podcast"
            entries.append(p)
        for n in data.get("newsletters", []):
            n["_type"] = "newsletter"
            entries.append(n)
        return entries
    except Exception as exc:
        logger.warning("Could not fetch index.json: %s", exc)
        return []


def _fetch_file_list(folder: str) -> List[Dict[str, Any]]:
    """Fetch directory listing from GitHub API."""
    url = f"{_settings.transcript_repo_api}/contents/{folder}"
    try:
        items = _fetch_json(url)
        return [i for i in items if i.get("type") == "file" and i["name"].endswith(".md")]
    except Exception as exc:
        logger.error("Could not fetch file list for %s: %s", folder, exc)
        return []


# ─── Markdown parsing ─────────────────────────────────────────────────────────

_HEADING_RE = re.compile(r"^#{1,4}\s+(.+)$", re.MULTILINE)
_SPEAKER_RE = re.compile(r"^\*\*([^*]+)\*\*:\s*(.*)$")  # **Speaker**: text


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_markdown_source(
    filename: str,
    content: str,
    source_type: str,
    index_entry: Optional[Dict[str, Any]] = None,
) -> ParsedSource:
    """Extract metadata and clean content from a markdown transcript."""
    slug = filename.replace(".md", "")

    # Try to get metadata from index entry
    title = slug.replace("-", " ").title()
    author = None
    canonical_url = None
    date_published = None
    word_count = None

    if index_entry:
        title = index_entry.get("title", title)
        author = index_entry.get("guest") or index_entry.get("author")
        canonical_url = index_entry.get("post_url")
        date_published = index_entry.get("date")
        word_count = index_entry.get("word_count")

    # If no index entry, try to parse frontmatter
    if not index_entry and content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            fm = content[3:end]
            for line in fm.split("\n"):
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip('"')
                elif line.startswith("guest:") or line.startswith("author:"):
                    author = line.split(":", 1)[1].strip()
                elif line.startswith("url:") or line.startswith("post_url:"):
                    canonical_url = line.split(":", 1)[1].strip()

    # Strip frontmatter for chunk processing
    body = content
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            body = content[end + 3:].strip()

    if word_count is None:
        word_count = len(body.split())

    return ParsedSource(
        external_id=f"{source_type}/{slug}",
        source_type=source_type,
        title=title,
        author=author,
        canonical_url=canonical_url,
        date_published=date_published,
        word_count=word_count,
        content=body,
        content_hash=_content_hash(body),
        meta={"filename": filename, "slug": slug},
    )


def _chunk_text(text: str) -> List[ParsedChunk]:
    """
    Split text into chunks preserving paragraph and speaker-turn boundaries.
    Uses heading-aware chunking with soft size limits and overlap.
    """
    chunks: List[ParsedChunk] = []
    current_heading: Optional[str] = None
    current_speaker: Optional[str] = None
    current_text: List[str] = []
    current_start: int = 0
    char_pos: int = 0
    chunk_index: int = 0

    def flush(heading, speaker, text_lines, start):
        nonlocal chunk_index
        block = "\n".join(text_lines).strip()
        if len(block) < 50:  # skip very short fragments
            return
        chunks.append(ParsedChunk(
            chunk_index=chunk_index,
            text=block,
            char_count=len(block),
            section_heading=heading,
            speaker=speaker,
            start_char=start,
        ))
        chunk_index += 1

    lines = text.split("\n")
    for line in lines:
        heading_match = _HEADING_RE.match(line)
        speaker_match = _SPEAKER_RE.match(line)

        if heading_match:
            # Flush current accumulation before new section
            if current_text:
                flush(current_heading, current_speaker, current_text, current_start)
                current_text = []
                current_start = char_pos
            current_heading = heading_match.group(1).strip()
            current_speaker = None
        elif speaker_match:
            speaker_name = speaker_match.group(1).strip()
            speaker_line = speaker_match.group(2).strip()
            # When speaker changes or chunk is big enough, flush
            if current_speaker and current_speaker != speaker_name and current_text:
                flush(current_heading, current_speaker, current_text, current_start)
                # Overlap: keep last line
                overlap = current_text[-1:] if current_text else []
                current_text = overlap
                current_start = char_pos
            current_speaker = speaker_name
            if speaker_line:
                current_text.append(f"**{speaker_name}**: {speaker_line}")
        else:
            current_text.append(line)

        char_pos += len(line) + 1  # +1 for newline

        # Soft flush on size
        current_size = sum(len(l) for l in current_text)
        if current_size >= CHUNK_SIZE:
            flush(current_heading, current_speaker, current_text, current_start)
            overlap = current_text[-2:] if len(current_text) >= 2 else current_text[-1:]
            current_text = overlap
            current_start = char_pos

    if current_text:
        flush(current_heading, current_speaker, current_text, current_start)

    return chunks


# ─── Persistence helpers ──────────────────────────────────────────────────────

def _upsert_source(db: Session, parsed: ParsedSource) -> Tuple[Source, bool]:
    """
    Insert source if new (by external_id), update content_hash if changed.
    Returns (source, is_new).
    """
    existing = db.query(Source).filter(Source.external_id == parsed.external_id).first()
    if existing:
        if existing.content_hash == parsed.content_hash:
            return existing, False  # unchanged
        # Content changed — delete old chunks and re-ingest
        db.query(TranscriptChunk).filter(TranscriptChunk.source_id == existing.id).delete()
        existing.content_hash = parsed.content_hash
        existing.word_count = parsed.word_count
        existing.meta = parsed.meta
        db.commit()
        return existing, True  # updated

    source = Source(
        id=str(uuid.uuid4()),
        source_type=parsed.source_type,
        title=parsed.title,
        author=parsed.author,
        canonical_url=parsed.canonical_url,
        external_id=parsed.external_id,
        content_hash=parsed.content_hash,
        word_count=parsed.word_count,
        date_published=parsed.date_published,
        meta=parsed.meta,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source, True


# ─── Main ingestion service ───────────────────────────────────────────────────

class IngestionService:
    """Orchestrates the full transcript ingestion pipeline."""

    def __init__(self, db: Session):
        self.db = db
        self.embedder = get_embedder()

    def _embed_chunks(self, chunks: List[ParsedChunk]) -> List[Optional[bytes]]:
        """Embed all chunk texts and return as serialized bytes."""
        texts = [c.text for c in chunks]
        vectors = self.embedder.embed_texts(texts)
        result = []
        for v in vectors:
            if v is not None:
                import numpy as np
                result.append(np.array(v, dtype=np.float32).tobytes())
            else:
                result.append(None)
        return result

    def _persist_chunks(
        self,
        source: Source,
        parsed_chunks: List[ParsedChunk],
        embeddings: List[Optional[bytes]],
    ) -> int:
        """Persist chunks to DB, return count inserted."""
        count = 0
        for parsed, emb in zip(parsed_chunks, embeddings):
            chunk = TranscriptChunk(
                id=str(uuid.uuid4()),
                source_id=source.id,
                chunk_index=parsed.chunk_index,
                text=parsed.text,
                char_count=parsed.char_count,
                section_heading=parsed.section_heading,
                speaker=parsed.speaker,
                start_char=parsed.start_char,
                embedding=emb,
                embedding_model=self.embedder.model_name(),
            )
            self.db.add(chunk)
            count += 1
        self.db.commit()
        return count

    def ingest_file(
        self,
        filename: str,
        content: str,
        source_type: str,
        index_entry: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingest a single markdown file. Returns status dict."""
        try:
            parsed = _parse_markdown_source(filename, content, source_type, index_entry)
            source, is_new = _upsert_source(self.db, parsed)

            if not is_new:
                return {"status": "skipped", "reason": "unchanged", "source_id": source.id}

            chunks = _chunk_text(parsed.content)
            embeddings = self._embed_chunks(chunks)
            chunk_count = self._persist_chunks(source, chunks, embeddings)

            return {
                "status": "ok",
                "source_id": source.id,
                "title": parsed.title,
                "chunks": chunk_count,
            }
        except Exception as exc:
            logger.error("Ingestion failed for %s: %s", filename, exc)
            return {"status": "error", "filename": filename, "error": str(exc)[:200]}

    def run_full_ingestion(self, job_id: str) -> None:
        """
        Run full ingestion from LennysNewsletter GitHub repo.
        Updates IngestionJob record throughout.
        """
        job = self.db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
        if not job:
            logger.error("Ingestion job %s not found", job_id)
            return

        job.status = "running"
        self.db.commit()

        errors: List[Dict[str, Any]] = []
        sources_created = 0
        chunks_created = 0
        processed = 0
        failed = 0

        try:
            # Fetch index for metadata
            index_entries = _fetch_index()
            index_by_filename: Dict[str, Dict] = {
                e.get("filename", "").split("/")[-1]: e for e in index_entries
            }

            # Collect files to process
            all_files: List[Tuple[str, str]] = []  # (filename, source_type)
            for folder, stype in [("podcasts", "podcast"), ("newsletters", "newsletter")]:
                for f in _fetch_file_list(folder):
                    all_files.append((f["name"], stype, f.get("download_url", "")))

            job.total_files = len(all_files)
            self.db.commit()

            # Process each file
            for filename, stype, download_url in all_files:
                try:
                    if not download_url:
                        download_url = (
                            f"https://raw.githubusercontent.com/LennysNewsletter/"
                            f"lennys-newsletterpodcastdata/main/{stype}s/{filename}"
                        )
                    content = _fetch_text(download_url)
                    idx_entry = index_by_filename.get(filename)
                    result = self.ingest_file(filename, content, stype, idx_entry)

                    if result["status"] == "error":
                        errors.append(result)
                        failed += 1
                    elif result["status"] == "ok":
                        sources_created += 1
                        chunks_created += result.get("chunks", 0)
                    processed += 1

                    # Update progress
                    job.processed_files = processed
                    job.failed_files = failed
                    job.sources_created = sources_created
                    job.chunks_created = chunks_created
                    self.db.commit()

                    time.sleep(0.1)  # Be polite to GitHub rate limits

                except Exception as exc:
                    logger.error("Failed to process %s: %s", filename, exc)
                    errors.append({"filename": filename, "error": str(exc)[:200]})
                    failed += 1
                    processed += 1
                    job.processed_files = processed
                    job.failed_files = failed
                    self.db.commit()

            # Fit TF-IDF if using simple embedder
            if isinstance(self.embedder, SimpleTFIDFEmbedder) and not self.embedder._fitted:
                self._fit_tfidf_on_corpus()

            job.status = "done" if not errors or sources_created > 0 else "failed"

        except Exception as exc:
            logger.error("Ingestion run failed: %s", exc)
            errors.append({"error": str(exc)[:200]})
            job.status = "failed"

        finally:
            job.completed_at = datetime.utcnow()
            job.errors = errors if errors else None
            self.db.commit()

    def _fit_tfidf_on_corpus(self) -> None:
        """Fit TF-IDF embedder on all stored chunks."""
        try:
            if not isinstance(self.embedder, SimpleTFIDFEmbedder):
                return
            chunks = self.db.query(TranscriptChunk).all()
            if not chunks:
                return
            texts = [c.text for c in chunks]
            self.embedder.fit(texts)
            logger.info("TF-IDF fitted on %d chunks", len(texts))
        except Exception as exc:
            logger.warning("TF-IDF fit failed: %s", exc)

    def fit_embedder_on_existing(self) -> None:
        """Public method to fit embedder on already-indexed corpus."""
        self._fit_tfidf_on_corpus()

    def get_stats(self) -> Dict[str, Any]:
        """Return ingestion statistics from DB."""
        source_count = self.db.query(Source).count()
        chunk_count = self.db.query(TranscriptChunk).count()
        last_job = (
            self.db.query(IngestionJob)
            .order_by(IngestionJob.started_at.desc())
            .first()
        )
        return {
            "source_count": source_count,
            "chunk_count": chunk_count,
            "last_job_id": last_job.id if last_job else None,
            "last_job_status": last_job.status if last_job else None,
            "last_ingestion": last_job.completed_at.isoformat() if last_job and last_job.completed_at else None,
        }
