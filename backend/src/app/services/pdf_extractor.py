from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


class PdfExtractionError(Exception):
    pass


class EncryptedPdfError(PdfExtractionError):
    pass


class NoExtractableTextError(PdfExtractionError):
    pass


def extract_pdf_pages(pdf_path: Path) -> list[ExtractedPage]:
    try:
        reader = PdfReader(pdf_path)
    except (PdfReadError, OSError) as error:
        raise PdfExtractionError(
            "The PDF could not be opened"
        ) from error

    if reader.is_encrypted:
        raise EncryptedPdfError(
            "Password-protected PDFs are not currently supported"
        )

    extracted_pages: list[ExtractedPage] = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as error:
            raise PdfExtractionError(
                f"Text extraction failed on page {page_number}"
            ) from error

        cleaned_text = text.replace("\x00", "").strip()

        extracted_pages.append(
            ExtractedPage(
                page_number=page_number,
                text=cleaned_text,
            )
        )

    has_any_text = any(
        extracted_page.text
        for extracted_page in extracted_pages
    )

    if not has_any_text:
        raise NoExtractableTextError(
            "No text could be extracted. The PDF may contain scanned images."
        )

    return extracted_pages