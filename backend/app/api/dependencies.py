"""Dependency injection for the application."""

from functools import lru_cache

from app.agents.features import DraftAgent, FinalizerAgent, RetrieverAgent, SafetyAgent
from app.agents.orchestrator import AgentOrchestrator
from app.llm.openai_provider import get_llm_provider
from app.rag.chunking import TextChunker
from app.rag.embedding import EmbeddingService
from app.rag.retrieval import RetrievalService
from app.safety.classifier import get_safety_classifier
from app.safety.policy import get_safety_policy
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService


@lru_cache
def get_text_chunker() -> TextChunker:
    """Get text chunker instance."""
    return TextChunker()


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance."""
    return EmbeddingService(get_llm_provider())


@lru_cache
def get_retrieval_service() -> RetrievalService:
    """Get retrieval service instance."""
    return RetrievalService(get_llm_provider())


@lru_cache
def get_document_service() -> DocumentService:
    """Get document service instance."""
    return DocumentService(
        get_text_chunker(),
        get_embedding_service(),
        get_llm_provider(),
    )


@lru_cache
def get_agent_orchestrator() -> AgentOrchestrator:
    """Get agent orchestrator instance."""
    retriever = RetrieverAgent(get_retrieval_service())
    drafter = DraftAgent(get_llm_provider())
    safety = SafetyAgent(get_safety_classifier(), get_safety_policy())
    finalizer = FinalizerAgent(get_safety_policy())

    return AgentOrchestrator(retriever, drafter, safety, finalizer)


@lru_cache
def get_chat_service() -> ChatService:
    """Get chat service instance."""
    return ChatService(get_agent_orchestrator())
