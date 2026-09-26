"""Token aware page chunks. Overlap retains context without crossing page citations."""
from dataclasses import dataclass

import tiktoken

from app.services.pdf_extractor import ExtractedPage

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 75


@dataclass(frozen=True)
class TextChunk:
    page_number: int
    chunk_index: int
    content: str
    token_count: int


def chunk_extracted_pages(pages: list[ExtractedPage], chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[TextChunk]:
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("Invalid chunk size or overlap")
    encoder = tiktoken.get_encoding("cl100k_base")
    chunks = []
    for page in pages:
        tokens = encoder.encode(page.text.strip())
        for start in range(0, len(tokens), chunk_size - chunk_overlap):
            window = tokens[start:start + chunk_size]
            if not window:
                break
            content = encoder.decode(window).strip()
            if content:
                chunks.append(TextChunk(page.page_number, len(chunks), content, len(window)))
            if start + chunk_size >= len(tokens):
                break
    return chunks
