from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.repositories.document import (
    get_document_by_id,
    get_documents,
)
from app.schemas.document import (
    DocumentProcessingResponse,
    DocumentResponse,
)
from app.services.document_processor import (
    DocumentNotFoundError,
    DocumentProcessingError,
    ProcessingResult,
    StoredDocumentNotFoundError,
    process_document,
)
from app.services.document_upload import (
    DocumentTooLargeError,
    DuplicateDocumentError,
    InvalidDocumentError,
    store_uploaded_pdf,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: Annotated[
        UploadFile,
        File(description="PDF document to upload"),
    ],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentResponse:
    try:
        return store_uploaded_pdf(
            file=file,
            db=db,
            settings=settings,
        )

    except DuplicateDocumentError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(error),
                "existing_document_id": str(
                    error.existing_document_id
                ),
            },
        ) from error

    except DocumentTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(error),
        ) from error

    except InvalidDocumentError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.post(
    "/{document_id}/process",
    response_model=DocumentProcessingResponse,
    status_code=status.HTTP_200_OK,
)
def process_uploaded_document(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProcessingResult:
    try:
        return process_document(
            document_id=document_id,
            db=db,
            settings=settings,
        )

    except DocumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except StoredDocumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except DocumentProcessingError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get(
    "",
    response_model=list[DocumentResponse],
)
def list_documents(
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[DocumentResponse]:
    return get_documents(
        db=db,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
def get_document(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> DocumentResponse:
    document = get_document_by_id(
        db=db,
        document_id=document_id,
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document