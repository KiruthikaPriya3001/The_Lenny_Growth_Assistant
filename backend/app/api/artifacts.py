"""Artifacts API — create, get, update artifacts."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.artifacts.artifact_generator import ArtifactGenerator
from app.db.session import get_db
from app.models.models import Artifact, Conversation
from app.providers.llm_providers import get_provider
from app.retrieval.retrieval_service import RetrievalService
from app.schemas.schemas import ArtifactCreate, ArtifactOut, ArtifactUpdate

router = APIRouter()


def _artifact_out(a: Artifact) -> ArtifactOut:
    return ArtifactOut(
        id=a.id,
        conversation_id=a.conversation_id,
        artifact_type=a.artifact_type,
        title=a.title,
        content=a.content,
        content_format=a.content_format,
        source_references=a.source_references,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


@router.post("/artifacts", response_model=ArtifactOut, status_code=201)
def create_artifact(body: ArtifactCreate, db: Session = Depends(get_db)):
    """Generate and persist an artifact from a conversation."""
    conv = db.query(Conversation).filter(Conversation.id == body.conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Conversation not found."})

    provider = get_provider()
    retrieval = RetrievalService(db)
    generator = ArtifactGenerator(db, provider, retrieval)

    result = generator.generate(
        conversation_id=body.conversation_id,
        prompt=body.prompt or "Generate a summary artifact",
        artifact_type=body.artifact_type,
        title=body.title,
    )

    if "error" in result:
        raise HTTPException(status_code=422, detail={"error_code": "GENERATION_FAILED", "message": result["error"]})

    artifact = db.query(Artifact).filter(Artifact.id == result["artifact_id"]).first()
    if not artifact:
        raise HTTPException(status_code=500, detail={"error_code": "INTERNAL_ERROR", "message": "Artifact not found after creation."})
    return _artifact_out(artifact)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactOut)
def get_artifact(artifact_id: str, db: Session = Depends(get_db)):
    """Get an artifact by ID."""
    a = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not a:
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Artifact not found."})
    return _artifact_out(a)


@router.patch("/artifacts/{artifact_id}", response_model=ArtifactOut)
def update_artifact(artifact_id: str, body: ArtifactUpdate, db: Session = Depends(get_db)):
    """Update artifact title or content."""
    a = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not a:
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Artifact not found."})
    if body.title is not None:
        a.title = body.title
    if body.content is not None:
        a.content = body.content
    db.commit()
    db.refresh(a)
    return _artifact_out(a)


@router.get("/sessions/{session_id}/artifacts", response_model=list)
def list_session_artifacts(session_id: str, db: Session = Depends(get_db)):
    """List all artifacts for a conversation."""
    conv = db.query(Conversation).filter(Conversation.id == session_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Conversation not found."})
    artifacts = (
        db.query(Artifact)
        .filter(Artifact.conversation_id == session_id)
        .order_by(Artifact.created_at.desc())
        .all()
    )
    return [_artifact_out(a) for a in artifacts]
