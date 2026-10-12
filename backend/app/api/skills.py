"""Skills API — Ship 30 essay generation endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Artifact, Conversation
from app.providers.llm_providers import get_provider
from app.retrieval.retrieval_service import RetrievalService
from app.schemas.schemas import ArtifactOut, EssayRequest
from app.skills.essay_skill import EssaySkill

import uuid

router = APIRouter()


@router.post("/skills/ship-30-essay", response_model=ArtifactOut, status_code=201)
def generate_essay(body: EssayRequest, db: Session = Depends(get_db)):
    """Generate a Ship 30 for 30-style ~1250-word grounded essay."""
    conv = db.query(Conversation).filter(Conversation.id == body.conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Conversation not found."})

    provider = get_provider()
    retrieval = RetrievalService(db)
    skill = EssaySkill(db, provider, retrieval)

    user_request = body.thesis or f"Write an essay about growth insights from Lenny's Podcast"
    result = skill.write(
        conversation_id=body.conversation_id,
        user_request=user_request,
        audience=body.audience or "product managers and growth practitioners",
        tone=body.tone or "conversational, evidence-backed",
    )

    if result.get("error"):
        raise HTTPException(status_code=500, detail={"error_code": "GENERATION_FAILED", "message": result["error"]})

    # Persist as artifact
    artifact = Artifact(
        id=str(uuid.uuid4()),
        conversation_id=body.conversation_id,
        artifact_type="essay",
        title=result.get("title", "Essay")[:500],
        content=result.get("content", ""),
        content_format="markdown",
        source_references=result.get("sources", []),
        meta={
            "word_count": result.get("word_count"),
            "grounding": result.get("grounding"),
            "model": result.get("model"),
            "provider": result.get("provider"),
        },
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)

    return ArtifactOut(
        id=artifact.id,
        conversation_id=artifact.conversation_id,
        artifact_type=artifact.artifact_type,
        title=artifact.title,
        content=artifact.content,
        content_format=artifact.content_format,
        source_references=artifact.source_references,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )
