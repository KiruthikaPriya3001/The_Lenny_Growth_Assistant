"""Messages API — send messages, get history."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agents.growth_agent import GrowthAgent
from app.db.session import get_db
from app.models.models import Conversation, Message
from app.schemas.schemas import MessageCreate, MessageList, MessageOut, SourceReference

router = APIRouter()


def _source_ref(s: dict) -> SourceReference:
    return SourceReference(
        chunk_id=s.get("chunk_id", ""),
        source_id=s.get("source_id", ""),
        title=s.get("title", ""),
        author=s.get("author"),
        url=s.get("url"),
        excerpt=s.get("excerpt", "")[:500],
        score=s.get("score", 0.0),
        section=s.get("section"),
    )


def _msg_out(msg: Message, db: Session) -> MessageOut:
    sources = None
    if msg.sources_used and msg.retrieval_meta:
        # retrieval_meta stored as list of source dicts
        pass
    return MessageOut(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        created_at=msg.created_at,
        model=msg.model,
        provider=msg.provider,
        status=msg.status,
        grounding=msg.grounding,
        duration_ms=msg.duration_ms,
        input_tokens=msg.input_tokens,
        output_tokens=msg.output_tokens,
    )


@router.post("/sessions/{session_id}/messages", response_model=MessageOut, status_code=201)
def send_message(
    session_id: str,
    body: MessageCreate,
    db: Session = Depends(get_db),
):
    """Send a user message and receive a grounded assistant response."""
    # Validate session exists
    conv = db.query(Conversation).filter(Conversation.id == session_id).first()
    if not conv:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "NOT_FOUND", "message": "Conversation not found."},
        )

    agent = GrowthAgent(db, provider_override=body.provider)
    response = agent.handle_message(
        conversation_id=session_id,
        user_content=body.content,
        mode=body.mode,
    )

    # Fetch the persisted assistant message
    last_msg = (
        db.query(Message)
        .filter(
            Message.conversation_id == session_id,
            Message.role == "assistant",
        )
        .order_by(Message.created_at.desc())
        .first()
    )

    if not last_msg:
        raise HTTPException(status_code=500, detail={"error_code": "INTERNAL_ERROR", "message": "Failed to persist response."})

    out = _msg_out(last_msg, db)
    # Attach sources from response
    out.sources = [_source_ref(s) for s in response.sources]
    out.grounding = response.grounding
    return out


@router.get("/sessions/{session_id}/messages", response_model=MessageList)
def get_messages(
    session_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get message history for a session. Isolated per session."""
    conv = db.query(Conversation).filter(Conversation.id == session_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Conversation not found."})

    total = db.query(Message).filter(Message.conversation_id == session_id).count()
    offset = (page - 1) * page_size
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == session_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return MessageList(
        items=[_msg_out(m, db) for m in msgs],
        total=total,
        page=page,
        page_size=page_size,
    )
