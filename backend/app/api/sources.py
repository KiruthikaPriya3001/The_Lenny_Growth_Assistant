"""Sources API — list indexed knowledge base sources."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Source, TranscriptChunk
from app.schemas.schemas import SourceList, SourceOut

router = APIRouter()


def _source_out(source: Source, db: Session) -> SourceOut:
    chunk_count = db.query(TranscriptChunk).filter(TranscriptChunk.source_id == source.id).count()
    return SourceOut(
        id=source.id,
        source_type=source.source_type,
        title=source.title,
        author=source.author,
        canonical_url=source.canonical_url,
        external_id=source.external_id,
        ingested_at=source.ingested_at,
        word_count=source.word_count,
        date_published=source.date_published,
        chunk_count=chunk_count,
    )


@router.get("/sources", response_model=SourceList)
def list_sources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_type: str = Query(None),
    search: str = Query(None),
    db: Session = Depends(get_db),
):
    """List indexed transcript sources with pagination."""
    q = db.query(Source)
    if source_type:
        q = q.filter(Source.source_type == source_type)
    if search:
        like = f"%{search}%"
        q = q.filter(
            Source.title.ilike(like) | Source.author.ilike(like)
        )
    total = q.count()
    offset = (page - 1) * page_size
    sources = q.order_by(
        Source.date_published.is_(None),
        Source.date_published.desc(),
    ).offset(offset).limit(page_size).all()
    return SourceList(
        items=[_source_out(s, db) for s in sources],
        total=total,
        page=page,
        page_size=page_size,
    )
