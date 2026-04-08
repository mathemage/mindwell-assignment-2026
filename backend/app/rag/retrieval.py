"""Retrieval service for semantic search."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Chunk, Document, Embedding
from app.llm.provider import LLMProvider

settings = get_settings()
logger = get_logger(__name__)


class RetrievalService:
    """Service for semantic search and retrieval."""

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize retrieval service.

        Args:
            llm_provider: LLM provider for generating query embeddings
        """
        self.llm_provider = llm_provider

    async def retrieve(
        self,
        db: Session,
        query: str,
        top_k: int = settings.top_k_retrieval,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant chunks for a query.

        Args:
            db: Database session
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of retrieved chunks with metadata
        """
        logger.info("Retrieving chunks", query_length=len(query), top_k=top_k)

        # Generate query embedding
        query_vector = await self.llm_provider.generate_embedding(query)

        # Perform vector similarity search
        distance_expr = Embedding.vector.cosine_distance(query_vector).label("distance")
        stmt = (
            select(
                Chunk,
                Document,
                distance_expr,
            )
            .join(Embedding, Chunk.id == Embedding.chunk_id)
            .join(Document, Chunk.document_id == Document.id)
            .order_by(distance_expr)
            .limit(top_k)
        )

        results = db.execute(stmt).all()

        # Format results with citations
        retrieved = []
        for chunk, document, distance in results:
            similarity = 1 - distance  # Convert distance to similarity

            retrieved.append(
                {
                    "chunk_id": chunk.id,
                    "text": chunk.text,
                    "similarity": similarity,
                    "citation": {
                        "document_id": document.id,
                        "document_title": document.title,
                        "section_heading": chunk.chunk_metadata.get("heading", ""),
                        "chunk_index": chunk.chunk_index,
                    },
                    "metadata": chunk.chunk_metadata,
                }
            )

        logger.info("Retrieved chunks", result_count=len(retrieved))
        return retrieved

    def get_chunk_context(
        self,
        db: Session,
        chunk_id: str,
        context_size: int = 1,
    ) -> str:
        """
        Get surrounding context for a chunk.

        Args:
            db: Database session
            chunk_id: Chunk ID
            context_size: Number of chunks before and after

        Returns:
            Combined context text
        """
        # Get the target chunk
        chunk = db.query(Chunk).filter(Chunk.id == chunk_id).first()
        if not chunk:
            return ""

        # Get surrounding chunks
        stmt = (
            select(Chunk)
            .where(Chunk.document_id == chunk.document_id)
            .where(
                Chunk.chunk_index.between(
                    chunk.chunk_index - context_size,
                    chunk.chunk_index + context_size,
                )
            )
            .order_by(Chunk.chunk_index)
        )

        chunks = db.execute(stmt).scalars().all()
        return "\n\n".join(c.text for c in chunks)
