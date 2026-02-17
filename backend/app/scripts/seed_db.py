"""Database seeding script."""

import asyncio
from pathlib import Path

from app.core.logging import get_logger, setup_logging
from app.db.connection import SessionLocal, init_db
from app.llm.openai_provider import get_llm_provider
from app.rag.chunking import TextChunker
from app.rag.embedding import EmbeddingService
from app.services.document_service import DocumentService

logger = get_logger(__name__)


async def seed_database() -> None:
    """Seed database with sample CBT documents."""
    setup_logging()
    logger.info("Starting database seed")

    # Initialize database
    init_db()

    db = SessionLocal()

    try:
        # Initialize services
        llm_provider = get_llm_provider()
        chunker = TextChunker()
        embedding_service = EmbeddingService(llm_provider)
        doc_service = DocumentService(chunker, embedding_service, llm_provider)

        # Load sample documents
        sample_docs_dir = Path(__file__).parent.parent.parent.parent / "data" / "sample_docs"

        if not sample_docs_dir.exists():
            logger.warning("Sample docs directory not found", path=str(sample_docs_dir))
            return

        # Ingest all markdown files
        for md_file in sample_docs_dir.glob("*.md"):
            logger.info("Ingesting document", filename=md_file.name)
            with open(md_file) as f:
                content = f.read()

            await doc_service.ingest_document(
                db=db,
                title=md_file.stem.replace("_", " ").title(),
                content=content,
                source_type="markdown",
                metadata={"source": "seed"},
            )

        logger.info("Database seeding completed")

    except Exception as e:
        logger.error("Database seeding failed", error=str(e), exc_info=True)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
