from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk


def replace_document_chunks(
    db: Session,
    *,
    document_id: UUID,
    chunks: list[DocumentChunk],
) -> None:
    delete_statement = delete(DocumentChunk).where(
        DocumentChunk.document_id == document_id
    )

    db.execute(delete_statement)

    db.add_all(chunks)