"""Sessions API — create, list, get, delete conversations."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Conversation, Message
from app.schemas.schemas import ConversationCreate, ConversationList, ConversationOut

router = APIRouter()


def _conv_out(conv: Conversation, db: Session) -> ConversationOut:
    msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
    return ConversationOut(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=msg_count,
    )


@router.post("/sessions", response_model=ConversationOut, status_code=201)
def create_session(body: ConversationCreate, db: Session = Depends(get_db)):
    """Create a new independent conversation session."""
    conv = Conversation(
        id=str(uuid.uuid4()),
        title=body.title or "New Conversation",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _conv_out(conv, db)


@router.get("/sessions", response_model=ConversationList)
def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all conversation sessions, most recent first."""
    total = db.query(Conversation).count()
    offset = (page - 1) * page_size
    convs = (
        db.query(Conversation)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return ConversationList(
        items=[_conv_out(c, db) for c in convs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/sessions/{session_id}", response_model=ConversationOut)
def get_session(session_id: str, db: Session = Depends(get_db)):
    """Get a specific conversation by ID."""
    conv = db.query(Conversation).filter(Conversation.id == session_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Conversation not found."})
    return _conv_out(conv, db)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a conversation and all its messages/artifacts."""
    conv = db.query(Conversation).filter(Conversation.id == session_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Conversation not found."})
    db.delete(conv)
    db.commit()
