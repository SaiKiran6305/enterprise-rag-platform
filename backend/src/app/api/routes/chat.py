from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import current_user
from app.models.conversation import Conversation, Message
from app.models.identity import User
from app.services.ai import OpenAIProvider
from app.services.answer import FALLBACK, format_context, validate_answer
from app.services.retrieval import search

router = APIRouter(prefix="/chat", tags=["Chat"])


class Query(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    conversation_id: UUID | None = None


def get_conversation(db: Session, user: User, conversation_id: UUID) -> Conversation:
    conversation = db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.workspace_id == user.workspace_id, Conversation.user_id == user.id))
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    return conversation


@router.post("/query")
def query(payload: Query, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], settings: Annotated[Settings, Depends(get_settings)]):
    conversation = get_conversation(db, user, payload.conversation_id) if payload.conversation_id else None
    previous = []
    if conversation:
        previous = list(db.scalars(select(Message).where(Message.conversation_id == conversation.id, Message.role == "user").order_by(Message.position.desc()).limit(2)))
    search_question = (f"Earlier question: {previous[0].content}\nFollow-up question: {payload.question}" if previous else payload.question)
    try:
        provider = OpenAIProvider(settings, user.workspace_id)
        hits = search(db, user.workspace_id, search_question, min(payload.top_k, settings.max_context_chunks), settings, provider)
        answer, citations = validate_answer(provider.answer(payload.question, format_context(hits)), hits) if hits else (FALLBACK, [])
    except Exception as exc:
        raise HTTPException(503, "Answer service unavailable") from exc
    if conversation is None:
        conversation = Conversation(workspace_id=user.workspace_id, user_id=user.id, title=payload.question[:160])
        db.add(conversation)
        db.flush()
    db.scalar(select(Conversation).where(Conversation.id == conversation.id).with_for_update())
    last_position = db.scalar(select(Message.position).where(Message.conversation_id == conversation.id).order_by(Message.position.desc()).limit(1))
    next_position = 0 if last_position is None else last_position + 1
    db.add_all([Message(conversation_id=conversation.id, position=next_position, role="user", content=payload.question, citations=[]), Message(conversation_id=conversation.id, position=next_position + 1, role="assistant", content=answer, citations=citations)])
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"answer": answer, "citations": citations, "conversation_id": str(conversation.id)}


@router.get("/conversations")
def conversations(db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    rows = db.scalars(select(Conversation).where(Conversation.user_id == user.id, Conversation.workspace_id == user.workspace_id).order_by(Conversation.updated_at.desc()).limit(100)).all()
    return [{"id": str(c.id), "title": c.title, "created_at": c.created_at} for c in rows]


@router.get("/conversations/{conversation_id}")
def conversation_detail(conversation_id: UUID, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    c = get_conversation(db, user, conversation_id)
    rows = db.scalars(select(Message).where(Message.conversation_id == c.id).order_by(Message.position).limit(200)).all()
    return {"id": str(c.id), "title": c.title, "messages": [{"id": str(m.id), "role": m.role, "content": m.content, "citations": m.citations, "created_at": m.created_at} for m in rows]}
