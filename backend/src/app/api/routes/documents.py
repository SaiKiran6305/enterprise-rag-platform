from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import current_user, editor
from app.models.document import Document, DocumentStatus
from app.models.identity import User
from app.repositories.document import get_document_by_id, get_documents
from app.schemas.document import DocumentResponse
from app.services.document_upload import DocumentTooLargeError, DuplicateDocumentError, InvalidDocumentError, store_uploaded_pdf
from app.worker import enqueue_document

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=201)
def upload_document(file: Annotated[UploadFile, File(description="PDF document")], db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(editor)], settings: Annotated[Settings, Depends(get_settings)]):
    count = db.scalar(select(func.count(Document.id)).where(Document.workspace_id == user.workspace_id))
    if count >= settings.max_documents_per_workspace:
        raise HTTPException(409, "Workspace document limit reached")
    try:
        doc = store_uploaded_pdf(file=file, db=db, settings=settings, workspace_id=user.workspace_id, owner_id=user.id)
    except DuplicateDocumentError as exc:
        raise HTTPException(409, {"message": str(exc), "existing_document_id": str(exc.existing_document_id)}) from exc
    except DocumentTooLargeError as exc:
        raise HTTPException(413, str(exc)) from exc
    except InvalidDocumentError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        enqueue_document(str(doc.id))
    except Exception as exc:
        raise HTTPException(503, {"message": "Queue unavailable; retry processing", "document_id": str(doc.id)}) from exc
    return doc


@router.post("/{document_id}/process", status_code=202)
def retry_document(document_id: UUID, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(editor)]):
    doc = get_document_by_id(db, document_id, user.workspace_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    stale = doc.status == DocumentStatus.PROCESSING and doc.updated_at < datetime.now(timezone.utc) - timedelta(minutes=15)
    if doc.status not in (DocumentStatus.UPLOADED, DocumentStatus.FAILED) and not stale:
        raise HTTPException(409, "Document is already processing or ready")
    if stale:
        doc.status = DocumentStatus.FAILED
        db.commit()
    try:
        enqueue_document(str(doc.id))
    except Exception as exc:
        raise HTTPException(503, "Queue unavailable") from exc
    return {"document_id": str(doc.id), "status": doc.status}


@router.get("", response_model=list[DocumentResponse])
def list_documents(db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)], offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return get_documents(db, user.workspace_id, offset, limit)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: UUID, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(current_user)]):
    doc = get_document_by_id(db, document_id, user.workspace_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: UUID, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(editor)], settings: Annotated[Settings, Depends(get_settings)]):
    doc = get_document_by_id(db, document_id, user.workspace_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    path = settings.upload_directory / doc.stored_filename
    db.delete(doc)
    db.commit()
    path.unlink(missing_ok=True)
