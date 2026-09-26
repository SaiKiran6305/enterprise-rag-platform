from app.services.pdf_extractor import ExtractedPage
from app.services.text_chunker import chunk_extracted_pages


def test_chunking_preserves_page_provenance_and_all_terms():
    pages = [ExtractedPage(1, "alpha beta gamma delta epsilon"), ExtractedPage(2, "zeta eta theta")]
    chunks = chunk_extracted_pages(pages, chunk_size=4, chunk_overlap=1)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert {c.page_number for c in chunks} == {1, 2}
    text = " ".join(c.content for c in chunks)
    assert all(word in text for word in "alpha beta gamma delta epsilon zeta eta theta".split())


def test_blank_pages_and_invalid_overlap():
    assert chunk_extracted_pages([ExtractedPage(1, "")]) == []
    try:
        chunk_extracted_pages([], 10, 10)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected overlap validation")
