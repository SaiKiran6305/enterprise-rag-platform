from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import get_settings
from app.services.document_upload import DocumentTooLargeError, InvalidDocumentError, store_uploaded_pdf
from uuid import uuid4


def pdf_file(name: str, data: bytes) -> UploadFile:
    return UploadFile(file=BytesIO(data), filename=name, headers=Headers({"content-type": "application/pdf"}))


def test_upload_rejects_non_pdf_without_creating_file(tmp_path: Path):
    settings = get_settings().model_copy(update={"upload_directory": tmp_path})
    with pytest.raises(InvalidDocumentError):
        store_uploaded_pdf(file=pdf_file("../../attack.pdf", b"not a PDF"), db=object(), settings=settings, workspace_id=uuid4(), owner_id=uuid4())
    assert list(tmp_path.iterdir()) == []


def test_oversize_upload_removes_partial_file(tmp_path: Path):
    settings = get_settings().model_copy(update={"upload_directory": tmp_path, "max_upload_size_bytes": 6})
    with pytest.raises(DocumentTooLargeError):
        store_uploaded_pdf(file=pdf_file("report.pdf", b"%PDF-abcdef"), db=object(), settings=settings, workspace_id=uuid4(), owner_id=uuid4())
    assert list(tmp_path.iterdir()) == []
