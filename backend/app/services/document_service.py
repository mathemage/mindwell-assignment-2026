"""Document management service."""

import io
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.errors import DocumentProcessingError
from app.core.logging import get_logger
from app.db.models import Chunk, Document
from app.llm.provider import LLMProvider
from app.rag.chunking import TextChunker
from app.rag.embedding import EmbeddingService

logger = get_logger(__name__)


class DocumentService:
    """Service for managing documents."""

    def __init__(
        self,
        chunker: TextChunker,
        embedding_service: EmbeddingService,
        llm_provider: LLMProvider,
    ):
        """
        Initialize document service.

        Args:
            chunker: Text chunker
            embedding_service: Embedding service
            llm_provider: LLM provider
        """
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.llm_provider = llm_provider

    async def ingest_document(
        self,
        db: Session,
        title: str,
        content: str,
        source_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """
        Ingest a document into the knowledge base.

        Args:
            db: Database session
            title: Document title
            content: Document content
            source_type: Source type (markdown, pdf, text)
            metadata: Optional metadata

        Returns:
            Created document

        Raises:
            DocumentProcessingError: If processing fails
        """
        logger.info("Ingesting document", title=title, source_type=source_type)

        try:
            # Create document
            document = Document(
                title=title,
                content=content,
                source_type=source_type,
                extra_metadata=metadata or {},
            )
            db.add(document)
            db.flush()

            # Chunk document
            if source_type == "markdown":
                chunks_data = self.chunker.chunk_markdown(
                    content,
                    metadata={"document_id": document.id, "title": title},
                )
            else:
                chunks_data = self.chunker.chunk_text(
                    content,
                    metadata={"document_id": document.id, "title": title},
                )

            # Create chunk records
            chunks = []
            for idx, chunk_data in enumerate(chunks_data):
                chunk = Chunk(
                    document_id=document.id,
                    chunk_index=idx,
                    text=chunk_data["text"],
                    chunk_metadata=chunk_data["metadata"],
                )
                db.add(chunk)
                chunks.append(chunk)

            db.flush()

            # Generate embeddings
            await self.embedding_service.embed_chunks(
                db,
                chunks,
                model_name=self.llm_provider.embedding_model,
            )

            db.commit()
            db.refresh(document)

            logger.info(
                "Document ingested successfully",
                document_id=document.id,
                chunk_count=len(chunks),
            )

            return document

        except Exception as e:
            db.rollback()
            logger.error("Failed to ingest document", error=str(e), exc_info=True)
            raise DocumentProcessingError(f"Failed to ingest document: {str(e)}") from e

    async def ingest_file(
        self,
        db: Session,
        filename: str,
        file_content: bytes,
    ) -> Document:
        """
        Ingest a file into the knowledge base.

        Args:
            db: Database session
            filename: File name
            file_content: File content bytes

        Returns:
            Created document

        Raises:
            DocumentProcessingError: If file processing fails
        """
        logger.info("Ingesting file", filename=filename)

        suffix = Path(filename).suffix.lower()

        try:
            if suffix == ".md":
                content = file_content.decode("utf-8")
                return await self.ingest_document(
                    db,
                    title=filename,
                    content=content,
                    source_type="markdown",
                )

            elif suffix == ".pdf":
                # Extract text from PDF
                pdf_reader = PdfReader(io.BytesIO(file_content))
                text_parts = []
                for page in pdf_reader.pages:
                    text_parts.append(page.extract_text())
                content = "\n\n".join(text_parts)

                return await self.ingest_document(
                    db,
                    title=filename,
                    content=content,
                    source_type="pdf",
                )

            elif suffix == ".txt":
                content = file_content.decode("utf-8")
                return await self.ingest_document(
                    db,
                    title=filename,
                    content=content,
                    source_type="text",
                )

            else:
                raise DocumentProcessingError(f"Unsupported file type: {suffix}")

        except Exception as e:
            logger.error("Failed to ingest file", error=str(e), exc_info=True)
            raise DocumentProcessingError(f"Failed to ingest file: {str(e)}") from e

    def list_documents(
        self,
        db: Session,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        """
        List documents in the knowledge base.

        Args:
            db: Database session
            limit: Maximum number of documents
            offset: Offset for pagination

        Returns:
            List of documents
        """
        return (
            db.query(Document)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_document(self, db: Session, document_id: str) -> Document | None:
        """
        Get a document by ID.

        Args:
            db: Database session
            document_id: Document ID

        Returns:
            Document or None
        """
        return db.query(Document).filter(Document.id == document_id).first()

    async def reindex_document(self, db: Session, document_id: str) -> Document:
        """
        Re-index a document (regenerate chunks and embeddings).

        Args:
            db: Database session
            document_id: Document ID

        Returns:
            Updated document

        Raises:
            DocumentProcessingError: If re-indexing fails
        """
        logger.info("Re-indexing document", document_id=document_id)

        document = self.get_document(db, document_id)
        if not document:
            raise DocumentProcessingError(f"Document not found: {document_id}")

        try:
            # Delete existing chunks (cascades to embeddings)
            db.query(Chunk).filter(Chunk.document_id == document_id).delete()
            db.flush()

            # Re-chunk and embed
            if document.source_type == "markdown":
                chunks_data = self.chunker.chunk_markdown(
                    document.content,
                    metadata={"document_id": document.id, "title": document.title},
                )
            else:
                chunks_data = self.chunker.chunk_text(
                    document.content,
                    metadata={"document_id": document.id, "title": document.title},
                )

            chunks = []
            for idx, chunk_data in enumerate(chunks_data):
                chunk = Chunk(
                    document_id=document.id,
                    chunk_index=idx,
                    text=chunk_data["text"],
                    chunk_metadata=chunk_data["metadata"],
                )
                db.add(chunk)
                chunks.append(chunk)

            db.flush()

            await self.embedding_service.embed_chunks(
                db,
                chunks,
                model_name=self.llm_provider.embedding_model,
            )

            db.commit()
            db.refresh(document)

            logger.info(
                "Document re-indexed successfully",
                document_id=document_id,
                chunk_count=len(chunks),
            )

            return document

        except Exception as e:
            db.rollback()
            logger.error("Failed to re-index document", error=str(e), exc_info=True)
            raise DocumentProcessingError(f"Failed to re-index document: {str(e)}") from e
