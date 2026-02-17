"""Embedding service for generating and storing embeddings."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Chunk, Embedding
from app.llm.provider import LLMProvider

logger = get_logger(__name__)


class EmbeddingService:
    """Service for managing embeddings."""

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize embedding service.

        Args:
            llm_provider: LLM provider for generating embeddings
        """
        self.llm_provider = llm_provider

    async def embed_chunk(
        self,
        db: Session,
        chunk: Chunk,
        model_name: str,
    ) -> Embedding:
        """
        Generate and store embedding for a chunk.

        Args:
            db: Database session
            chunk: Chunk to embed
            model_name: Name of embedding model

        Returns:
            Created embedding
        """
        logger.info("Generating embedding for chunk", chunk_id=chunk.id)

        # Generate embedding
        vector = await self.llm_provider.generate_embedding(chunk.text)

        # Create embedding record
        embedding = Embedding(
            chunk_id=chunk.id,
            vector=vector,
            model_name=model_name,
        )

        db.add(embedding)
        db.commit()
        db.refresh(embedding)

        logger.info("Embedding created", embedding_id=embedding.id)
        return embedding

    async def embed_chunks(
        self,
        db: Session,
        chunks: list[Chunk],
        model_name: str,
    ) -> list[Embedding]:
        """
        Generate and store embeddings for multiple chunks.

        Args:
            db: Database session
            chunks: Chunks to embed
            model_name: Name of embedding model

        Returns:
            Created embeddings
        """
        logger.info("Generating embeddings for chunks", chunk_count=len(chunks))

        embeddings = []
        for chunk in chunks:
            embedding = await self.embed_chunk(db, chunk, model_name)
            embeddings.append(embedding)

        logger.info("All embeddings created", embedding_count=len(embeddings))
        return embeddings

    def get_embedding(self, db: Session, chunk_id: str) -> Embedding | None:
        """
        Get embedding for a chunk.

        Args:
            db: Database session
            chunk_id: Chunk ID

        Returns:
            Embedding or None
        """
        stmt = select(Embedding).where(Embedding.chunk_id == chunk_id)
        return db.execute(stmt).scalar_one_or_none()
