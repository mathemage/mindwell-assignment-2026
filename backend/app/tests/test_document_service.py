"""Tests for document service."""

import io

import pytest
from pypdf import PdfWriter

from app.core.errors import DocumentProcessingError
from app.llm.openai_provider import OpenAIProvider
from app.rag.chunking import TextChunker
from app.rag.embedding import EmbeddingService
from app.services.document_service import DocumentService


@pytest.fixture
def document_service(test_db):
    """Create document service for testing."""
    llm_provider = OpenAIProvider()
    chunker = TextChunker()
    embedding_service = EmbeddingService(llm_provider)
    return DocumentService(chunker, embedding_service, llm_provider)


@pytest.mark.asyncio
async def test_pdf_with_no_text(test_db, document_service):
    """Test PDF with no extractable text raises error."""
    # Create a blank PDF (no text)
    pdf_writer = PdfWriter()
    pdf_writer.add_blank_page(width=200, height=200)

    pdf_bytes = io.BytesIO()
    pdf_writer.write(pdf_bytes)
    pdf_bytes.seek(0)

    with pytest.raises(DocumentProcessingError, match="no extractable text"):
        await document_service.ingest_file(
            test_db,
            "blank.pdf",
            pdf_bytes.getvalue()
        )
