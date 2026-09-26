from dataclasses import dataclass

from app.services.pdf_extractor import ExtractedPage


DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200


@dataclass(frozen=True)
class TextChunk:
    page_number: int
    chunk_index: int
    content: str


def chunk_extracted_pages(
    pages: list[ExtractedPage],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError(
            "Chunk size must be greater than zero"
        )

    if chunk_overlap < 0:
        raise ValueError(
            "Chunk overlap cannot be negative"
        )

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "Chunk overlap must be smaller than chunk size"
        )

    chunks: list[TextChunk] = []
    chunk_index = 0

    for page in pages:
        page_text = page.text.strip()

        if not page_text:
            continue

        start = 0

        while start < len(page_text):
            proposed_end = min(
                start + chunk_size,
                len(page_text),
            )

            end = find_natural_break(
                text=page_text,
                start=start,
                proposed_end=proposed_end,
            )

            content = page_text[start:end].strip()

            if content:
                chunks.append(
                    TextChunk(
                        page_number=page.page_number,
                        chunk_index=chunk_index,
                        content=content,
                    )
                )

                chunk_index += 1

            if end >= len(page_text):
                break

            next_start = end - chunk_overlap

            start = max(
                start + 1,
                next_start,
            )

    return chunks


def find_natural_break(
    *,
    text: str,
    start: int,
    proposed_end: int,
) -> int:
    if proposed_end >= len(text):
        return len(text)

    minimum_break_position = start + (
        (proposed_end - start) * 3 // 4
    )

    paragraph_break = text.rfind(
        "\n\n",
        minimum_break_position,
        proposed_end,
    )

    if paragraph_break != -1:
        return paragraph_break + 2

    sentence_break = text.rfind(
        ". ",
        minimum_break_position,
        proposed_end,
    )

    if sentence_break != -1:
        return sentence_break + 1

    space_break = text.rfind(
        " ",
        minimum_break_position,
        proposed_end,
    )

    if space_break != -1:
        return space_break

    return proposed_end