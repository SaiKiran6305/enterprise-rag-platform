from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    stored_filename: str
    content_type: str
    file_size: int
    content_hash: str | None
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )

class DocumentProcessingResponse(BaseModel):
    document_id: UUID
    status: DocumentStatus
    pages_extracted: int
    chunks_created: int