from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.ai import OpenAIProvider


@dataclass(frozen=True)
class SearchHit:
    chunk: DocumentChunk
    document: Document
    similarity_score: float


def search(db: Session, workspace_id: UUID, question: str, top_k: int, settings: Settings, provider: OpenAIProvider | None = None) -> list[SearchHit]:
    # Tenant condition is in SQL before ranking and before any excerpt reaches the model.
    has_documents = db.scalar(select(Document.id).where(Document.workspace_id == workspace_id, Document.status == DocumentStatus.READY).limit(1))
    if not has_documents:
        return []
    vector = (provider or OpenAIProvider(settings, workspace_id)).embed_query(question)
    distance = DocumentChunk.embedding.cosine_distance(vector)
    stmt = (select(DocumentChunk, Document, distance.label("distance"))
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.workspace_id == workspace_id, Document.status == DocumentStatus.READY, DocumentChunk.embedding.is_not(None))
            .order_by(distance).limit(top_k))
    return [SearchHit(chunk, document, max(-1.0, min(1.0, 1 - float(score)))) for chunk, document, score in db.execute(stmt) if 1 - float(score) >= settings.retrieval_threshold]
