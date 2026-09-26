from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.repositories.document import get_document_by_id
from app.repositories.document_chunk import replace_document_chunks
from app.services.pdf_extractor import extract_pdf_pages
from app.services.text_chunker import chunk_extracted_pages

import logging


logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ProcessingResult:
    document_id: UUID
    status: DocumentStatus
    pages_extracted: int
    chunks_created: int


class DocumentNotFoundError(Exception):
    pass


class StoredDocumentNotFoundError(Exception):
    pass


class DocumentProcessingError(Exception):
    pass


def process_document(
    *,
    document_id: UUID,
    db: Session,
    settings: Settings,
) -> ProcessingResult:
    document = get_document_by_id(
        db=db,
        document_id=document_id,
    )

    if document is None:
        raise DocumentNotFoundError(
            "Document not found"
        )

    pdf_path = (
        settings.upload_directory
        / document.stored_filename
    )

    if not pdf_path.exists():
        raise StoredDocumentNotFoundError(
            "The stored PDF file could not be found"
        )

    document.status = DocumentStatus.PROCESSING
    document.error_message = None

    db.commit()

    try:
        extracted_pages = extract_pdf_pages(pdf_path)

        text_chunks = chunk_extracted_pages(
            extracted_pages
        )

        if not text_chunks:
            raise DocumentProcessingError(
                "No chunks could be created from the PDF"
            )

        database_chunks = [
            DocumentChunk(
                document_id=document.id,
                page_number=text_chunk.page_number,
                chunk_index=text_chunk.chunk_index,
                content=text_chunk.content,
                section_title=None,
                token_count=None,
                embedding=None,
            )
            for text_chunk in text_chunks
        ]

        replace_document_chunks(
            db,
            document_id=document.id,
            chunks=database_chunks,
        )

        document.status = DocumentStatus.READY
        document.error_message = None

        db.commit()

        return ProcessingResult(
            document_id=document.id,
            status=document.status,
            pages_extracted=len(extracted_pages),
            chunks_created=len(database_chunks),
        )

    except Exception as error:
        db.rollback()

        failed_document = get_document_by_id(
            db=db,
            document_id=document_id,
        )

        if failed_document is not None:
            failed_document.status = DocumentStatus.FAILED
            failed_document.error_message = str(error)[:1000]
            db.commit()

        if isinstance(error, DocumentProcessingError):
            raise

        raise DocumentProcessingError(
            f"Document processing failed: {error}"
        ) from error
    
    except Exception as error:
        db.rollback()

        logger.exception(
            "Processing failed for document %s",
            document_id,
        )

        failed_document = get_document_by_id(
            db=db,
            document_id=document_id,
        )

        if failed_document is not None:
            failed_document.status = DocumentStatus.FAILED
            failed_document.error_message = (
                "Document processing failed"
            )
            db.commit()

        if isinstance(error, DocumentProcessingError):
            raise

        raise DocumentProcessingError(
            "Document processing failed"
        ) from error