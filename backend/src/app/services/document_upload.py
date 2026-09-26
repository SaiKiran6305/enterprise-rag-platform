from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Document
from app.repositories.document import (
    create_document,
    get_document_by_content_hash,
)

COPY_CHUNK_SIZE = 1024 * 1024

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
}


class InvalidDocumentError(ValueError):
    pass


class DocumentTooLargeError(ValueError):
    pass


def store_uploaded_pdf(
    *,
    file: UploadFile,
    db: Session,
    settings: Settings,
    workspace_id: UUID,
    owner_id: UUID,
) -> Document:
    if not file.filename:
        raise InvalidDocumentError(
            "A filename is required"
        )

    normalized_filename = file.filename.replace(
        "\\",
        "/",
    )

    original_filename = Path(
        normalized_filename
    ).name
    if len(original_filename) > 255:
        raise InvalidDocumentError("Filename is too long")

    if Path(original_filename).suffix.lower() != ".pdf":
        raise InvalidDocumentError(
            "Only PDF files are allowed"
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidDocumentError(
            "Only PDF files are allowed"
        )

    file.file.seek(0)
    pdf_signature = file.file.read(5)
    file.file.seek(0)

    if pdf_signature != b"%PDF-":
        raise InvalidDocumentError(
            "The uploaded file does not appear to be a valid PDF"
        )

    settings.upload_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = f"{uuid4()}.pdf"

    destination = (
        settings.upload_directory
        / stored_filename
    )

    total_bytes = 0
    content_hasher = sha256()

    try:
        with destination.open("xb") as output_file:
            while chunk := file.file.read(
                COPY_CHUNK_SIZE
            ):
                total_bytes += len(chunk)

                if (
                    total_bytes
                    > settings.max_upload_size_bytes
                ):
                    raise DocumentTooLargeError(
                        "The PDF exceeds the maximum allowed size"
                    )

                content_hasher.update(chunk)
                output_file.write(chunk)

        content_hash = content_hasher.hexdigest()
        if total_bytes == 0:
            raise InvalidDocumentError("The PDF is empty")

        existing_document = get_document_by_content_hash(
            db,
            content_hash=content_hash,
            workspace_id=workspace_id,
        )

        if existing_document is not None:
            raise DuplicateDocumentError(
                existing_document_id=existing_document.id,
            )

        document = create_document(
            db,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=(
                file.content_type
                or "application/pdf"
            ),
            file_size=total_bytes,
            content_hash=content_hash,
            workspace_id=workspace_id,
            owner_id=owner_id,
        )

        return document

    except Exception:
        destination.unlink(missing_ok=True)
        raise

class DuplicateDocumentError(ValueError):
    def __init__(
        self,
        existing_document_id: UUID,
    ) -> None:
        self.existing_document_id = existing_document_id

        super().__init__(
            "This document has already been uploaded"
        )
