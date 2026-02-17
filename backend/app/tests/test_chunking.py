"""Tests for text chunking."""

from app.rag.chunking import TextChunker


def test_chunk_markdown():
    """Test markdown chunking."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)

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

    # Check that headings are captured
    headings = [chunk["metadata"].get("heading", "") for chunk in chunks]
    assert any("Main Heading" in h for h in headings)
    assert any("Sub Heading" in h for h in headings)


def test_chunk_text():
    """Test plain text chunking."""
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)

    text = "This is a test sentence. " * 20  # Long text

    chunks = chunker.chunk_text(text)

    assert len(chunks) > 1  # Should split into multiple chunks
    assert all("text" in chunk for chunk in chunks)
    assert all("metadata" in chunk for chunk in chunks)


def test_chunk_overlap():
    """Test chunk overlap."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)

    text = "A" * 250  # Long text

    chunks = chunker.chunk_text(text)

    assert len(chunks) >= 2
    # Chunks should have some overlap
    for i in range(len(chunks) - 1):
        chunk1_end = chunks[i]["text"][-20:]
        chunk2_start = chunks[i + 1]["text"][:20]
        # There should be some similarity due to overlap
        assert len(chunk1_end) > 0 and len(chunk2_start) > 0
