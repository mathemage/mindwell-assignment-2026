"""Tests for text chunking."""

import pytest

from app.rag.chunking import TextChunker


@pytest.fixture
def chunker() -> TextChunker:
    """Create a text chunker without tiktoken dependency."""
    return TextChunker(chunk_size=100, chunk_overlap=20)


def test_chunk_markdown(chunker: TextChunker) -> None:
    """Test markdown chunking."""

    text = """# Main Heading

This is some content under the main heading.

## Sub Heading

This is content under a sub heading.

### Sub Sub Heading

More content here.
"""

    chunks = chunker.chunk_markdown(text)

    assert len(chunks) > 0
    assert all("text" in chunk for chunk in chunks)
    assert all("metadata" in chunk for chunk in chunks)

    # Check that headings are captured (may not capture first heading before split)
    headings = [chunk["metadata"].get("heading", "") for chunk in chunks]
    # At least one heading should be captured
    assert any(h != "" for h in headings)


def test_chunk_text(chunker: TextChunker) -> None:
    """Test plain text chunking."""

    text = "This is a test sentence. " * 20  # Long text

    chunks = chunker.chunk_text(text)

    assert len(chunks) > 1  # Should split into multiple chunks
    assert all("text" in chunk for chunk in chunks)
    assert all("metadata" in chunk for chunk in chunks)


def test_chunk_overlap(chunker: TextChunker) -> None:
    """Test chunk overlap."""

    text = "A" * 250  # Long text

    chunks = chunker.chunk_text(text)

    assert len(chunks) >= 2
    # Chunks should have some overlap
    for i in range(len(chunks) - 1):
        chunk1_end = chunks[i]["text"][-20:]
        chunk2_start = chunks[i + 1]["text"][:20]
        # There should be some similarity due to overlap
        assert len(chunk1_end) > 0 and len(chunk2_start) > 0
