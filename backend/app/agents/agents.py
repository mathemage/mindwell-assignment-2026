"""Agent implementations for the RAG pipeline."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.llm.provider import LLMProvider
from app.rag.retrieval import RetrievalService
from app.safety.classifier import SafetyClassifier, SafetyResult
from app.safety.policy import SafetyOutcome, SafetyPolicy

logger = get_logger(__name__)


class RetrieverAgent:
    """Agent for retrieving relevant information."""

    def __init__(self, retrieval_service: RetrievalService):
        """
        Initialize retriever agent.

        Args:
            retrieval_service: Retrieval service
        """
        self.retrieval_service = retrieval_service

    async def retrieve(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant chunks for a query.

        Args:
            db: Database session
            query: User query
            top_k: Number of top results

        Returns:
            Retrieved chunks
        """
        logger.info("RetrieverAgent: Retrieving chunks", query=query)
        chunks = await self.retrieval_service.retrieve(db, query, top_k)
        logger.info("RetrieverAgent: Retrieved chunks", count=len(chunks))
        return chunks


class DraftAgent:
    """Agent for generating draft responses."""

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize draft agent.

        Args:
            llm_provider: LLM provider
        """
        self.llm_provider = llm_provider

    async def draft_response(
        self,
        query: str,
        retrieved_chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Generate a draft response.

        Args:
            query: User query
            retrieved_chunks: Retrieved context chunks

        Returns:
            Draft response with citations
        """
        logger.info("DraftAgent: Generating draft response")

        if not retrieved_chunks:
            return {
                "content": "I don't have enough information to answer that question. Could you please rephrase or provide more context?",
                "citations": [],
            }

        # Build context from chunks
        context = self._build_context(retrieved_chunks)

        # Create system prompt
        system_prompt = """You are a helpful AI assistant for a cognitive behavioral therapy (CBT) program.

Your role:
- Answer questions based ONLY on the provided context
- Always cite your sources using [Doc: title, Section: heading]
- If the context doesn't contain the answer, say so clearly
- Be empathetic and supportive
- Use clear, accessible language
- DO NOT provide medical diagnoses or prescribe treatments

If you're unsure or the information isn't in the context, ask for clarification."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ]

        # Generate response
        result = await self.llm_provider.chat_completion(
            messages=messages,
            temperature=0.7,
        )

        # Extract citations from response
        citations = self._extract_citations(result["content"], retrieved_chunks)

        return {
            "content": result["content"],
            "citations": citations,
            "usage": result["usage"],
        }

    def _build_context(self, chunks: list[dict[str, Any]]) -> str:
        """Build context string from chunks."""
        context_parts = []

        for chunk in chunks:
            citation = chunk["citation"]
            heading = citation.get("section_heading", "")
            context_parts.append(
                f"[Doc: {citation['document_title']}"
                + (f", Section: {heading}" if heading else "")
                + f"]\n{chunk['text']}"
            )

        return "\n\n".join(context_parts)

    def _extract_citations(
        self,
        content: str,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract citations from response."""
        # Return all chunks as potential citations
        return [
            {
                "document_id": chunk["citation"]["document_id"],
                "document_title": chunk["citation"]["document_title"],
                "section_heading": chunk["citation"].get("section_heading", ""),
                "chunk_index": chunk["citation"]["chunk_index"],
                "text_snippet": chunk["text"][:200] + "..."
                if len(chunk["text"]) > 200
                else chunk["text"],
            }
            for chunk in chunks
        ]


class SafetyAgent:
    """Agent for safety checks."""

    def __init__(
        self,
        classifier: SafetyClassifier,
        policy: SafetyPolicy,
    ):
        """
        Initialize safety agent.

        Args:
            classifier: Safety classifier
            policy: Safety policy
        """
        self.classifier = classifier
        self.policy = policy

    def check_input(self, message: str) -> SafetyResult:
        """
        Check input message for safety.

        Args:
            message: User message

        Returns:
            Safety result
        """
        logger.info("SafetyAgent: Checking input")
        result = self.classifier.check_message(message)
        logger.info("SafetyAgent: Input check result", outcome=result.outcome.value)
        return result

    def check_output(
        self,
        response: str,
        retrieved_chunks: list[dict[str, Any]],
    ) -> SafetyResult:
        """
        Check output response for safety.

        Args:
            response: Generated response
            retrieved_chunks: Context chunks

        Returns:
            Safety result
        """
        logger.info("SafetyAgent: Checking output")
        result = self.classifier.check_response(response, retrieved_chunks)
        logger.info("SafetyAgent: Output check result", outcome=result.outcome.value)
        return result


class FinalizerAgent:
    """Agent for finalizing responses."""

    def __init__(self, policy: SafetyPolicy):
        """
        Initialize finalizer agent.

        Args:
            policy: Safety policy
        """
        self.policy = policy

    def finalize(
        self,
        draft: dict[str, Any],
        safety_result: SafetyResult,
    ) -> dict[str, Any]:
        """
        Finalize response based on safety check.

        Args:
            draft: Draft response
            safety_result: Safety check result

        Returns:
            Final response
        """
        logger.info("FinalizerAgent: Finalizing response")

        if safety_result.outcome == SafetyOutcome.ESCALATED:
            # Crisis detected - return emergency resources
            return {
                "content": f"I'm concerned about what you've shared. {self.policy.EMERGENCY_RESOURCES}",
                "citations": [],
                "safety_outcome": safety_result.outcome.value,
                "safety_reason": safety_result.reason,
                "violation_type": safety_result.violation_type.value
                if safety_result.violation_type
                else None,
                "severity": safety_result.severity,
                "confidence": safety_result.confidence,
            }

        elif safety_result.outcome == SafetyOutcome.REFUSED:
            # Policy violation - return appropriate message
            if safety_result.violation_type and "medical" in safety_result.violation_type.value:
                content = self.policy.MEDICAL_DISCLAIMER
            else:
                content = "I'm unable to assist with that request. " + safety_result.reason

            return {
                "content": content,
                "citations": [],
                "safety_outcome": safety_result.outcome.value,
                "safety_reason": safety_result.reason,
                "violation_type": safety_result.violation_type.value
                if safety_result.violation_type
                else None,
                "severity": safety_result.severity,
                "confidence": safety_result.confidence,
            }

        # OK - return draft response
        return {
            "content": draft["content"],
            "citations": draft["citations"],
            "safety_outcome": safety_result.outcome.value,
            "usage": draft.get("usage", {}),
            "violation_type": None,
            "severity": None,
            "confidence": safety_result.confidence,
        }
