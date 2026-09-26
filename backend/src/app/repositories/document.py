from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


def get_documents(
    db: Session,
    workspace_id: UUID,
    offset: int = 0,
    limit: int = 100,
) -> Sequence[Document]:
    statement = (
        select(Document).where(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return db.scalars(statement).all()


def get_document_by_id(
    db: Session,
    document_id: UUID,
    workspace_id: UUID,
) -> Document | None:
    return db.scalar(select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id))

def create_document(
    db: Session,
    *,
    original_filename: str,
    stored_filename: str,
    content_type: str,
    file_size: int,
    content_hash: str,
    workspace_id: UUID,
    owner_id: UUID,
) -> Document:
    document = Document(
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=content_type,
        file_size=file_size,
        content_hash=content_hash,
        workspace_id=workspace_id,
        owner_id=owner_id,
    )

    db.add(document)

    try:
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        raise

    return document

def get_document_by_content_hash(
    db: Session,
    *,
    content_hash: str,
    workspace_id: UUID,
) -> Document | None:
    statement = select(Document).where(
        Document.content_hash == content_hash, Document.workspace_id == workspace_id
    )

    return db.scalar(statement)
