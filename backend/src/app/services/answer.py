import re

from app.services.retrieval import SearchHit

FALLBACK = "I could not find this information in the available documents."
SOURCE_PATTERN = re.compile(r"\[SOURCE-(\d+)\]")


def validate_answer(answer: str, hits: list[SearchHit]) -> tuple[str, list[dict]]:
    if not answer.strip() or answer.strip() == FALLBACK:
        return FALLBACK, []
    ids = [int(x) for x in SOURCE_PATTERN.findall(answer)]
    if not ids or any(i < 1 or i > len(hits) for i in ids) or re.search(r"\[SOURCE-[^\]]+\]", SOURCE_PATTERN.sub("", answer)):
        return FALLBACK, []
    citations = []
    for i in dict.fromkeys(ids):
        hit = hits[i - 1]
        citations.append({"source_id": f"SOURCE-{i}", "document_id": str(hit.document.id), "document_name": hit.document.original_filename, "page_number": hit.chunk.page_number, "section_title": hit.chunk.section_title, "excerpt": hit.chunk.content[:2400], "chunk_id": str(hit.chunk.id)})
    return answer.strip(), citations


def format_context(hits: list[SearchHit]) -> str:
    return "\n\n".join(f"[SOURCE-{i}] document={h.document.original_filename!r} page={h.chunk.page_number}\n{h.chunk.content[:2400]}" for i, h in enumerate(hits, 1))
