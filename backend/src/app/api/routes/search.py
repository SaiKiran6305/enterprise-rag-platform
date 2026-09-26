from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import current_user
from app.models.identity import User
from app.services.retrieval import search

router = APIRouter(prefix="/search", tags=["Search"])


class SearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


@router.post("")
def semantic_search(payload: SearchRequest, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], settings: Annotated[Settings, Depends(get_settings)]):
    try:
        hits = search(db, user.workspace_id, payload.question, payload.top_k, settings)
    except Exception as exc:
        raise HTTPException(503, "Search service unavailable") from exc
    return {"results": [{"chunk_id": str(h.chunk.id), "document_id": str(h.document.id), "document_name": h.document.original_filename, "page_number": h.chunk.page_number, "section_title": h.chunk.section_title, "content": h.chunk.content, "similarity_score": round(h.similarity_score, 4)} for h in hits]}
