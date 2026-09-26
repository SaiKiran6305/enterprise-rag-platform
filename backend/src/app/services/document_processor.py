"""Idempotent document processing in a separate RQ worker."""
import logging
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk, EMBEDDING_DIMENSION
from app.services.ai import OpenAIProvider
from app.services.pdf_extractor import extract_pdf_pages
from app.services.text_chunker import chunk_extracted_pages

logger = logging.getLogger(__name__)


def process_document(document_id: str) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        document = db.scalar(select(Document).where(Document.id == UUID(document_id)).with_for_update(skip_locked=True))
        if document is None or document.status in (DocumentStatus.READY, DocumentStatus.PROCESSING):
            return
        document.status = DocumentStatus.PROCESSING
        document.error_message = None
        stored_filename = document.stored_filename
        db.commit()
        try:
            pages = extract_pdf_pages(settings.upload_directory / stored_filename)
            chunks = chunk_extracted_pages(pages)
            if not chunks:
                raise ValueError("No extractable text in PDF")
            embeddings = OpenAIProvider(settings, document.workspace_id).embed_documents([c.content for c in chunks])
            if len(embeddings) != len(chunks) or any(len(e) != EMBEDDING_DIMENSION for e in embeddings):
                raise ValueError("Embedding response has an unexpected shape")
            document = db.get(Document, UUID(document_id))
            if document is None:
                return
            db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
            db.add_all(DocumentChunk(document_id=document.id, page_number=c.page_number, chunk_index=c.chunk_index, content=c.content, section_title=None, token_count=c.token_count, embedding=e) for c, e in zip(chunks, embeddings))
            document.status = DocumentStatus.READY
            db.commit()
            logger.info("Processed document %s: %s chunks", document_id, len(chunks))
        except Exception:
            db.rollback()
            logger.exception("Processing failed for %s", document_id)
            document = db.get(Document, UUID(document_id))
            if document:
                document.status = DocumentStatus.FAILED
                document.error_message = "Processing failed. Check worker logs or retry."
                db.commit()
            raise
