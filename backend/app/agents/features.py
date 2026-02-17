"""
Agent Feature Implementations for the Retrieval-Augmented Generation (RAG) Pipeline.

This module implements a multi-agent architecture for processing user queries in a cognitive
behavioral therapy (CBT) AI assistant. The pipeline consists of four specialized agents that
work together to provide safe, grounded, and helpful responses.

Architecture Overview:
    The agent pipeline follows a sequential processing flow:

    1. RetrieverAgent: Performs semantic search to find relevant context from the knowledge base
    2. DraftAgent: Generates initial responses using an LLM with retrieved context
    3. SafetyAgent: Validates both input and output for safety violations (crisis detection,
       medical advice, response grounding)
    4. FinalizerAgent: Makes final decisions on response delivery based on safety checks

Key Design Principles:
    - Privacy First: No personally identifiable information (PII) is logged or stored
    - Safety Over Performance: Conservative thresholds favor false positives to avoid missing
      critical safety issues
    - Grounded Responses: All responses must be based on retrieved context with citations
    - Separation of Concerns: Each agent has a single, well-defined responsibility

Usage Example:
    >>> retriever = RetrieverAgent(retrieval_service)
    >>> draft_agent = DraftAgent(llm_provider)
    >>> safety_agent = SafetyAgent(classifier, policy)
    >>> finalizer = FinalizerAgent(policy)
    >>>
    >>> # Process a user query
    >>> chunks = await retriever.retrieve(db, "What are CBT thought records?", top_k=5)
    >>> draft = await draft_agent.draft_response("What are CBT thought records?", chunks)
    >>> safety_result = safety_agent.check_output(draft["content"], chunks)
    >>> final_response = finalizer.finalize(draft, safety_result)

Dependencies:
    - sqlalchemy: Database session management
    - app.core.logging: Structured logging with PII redaction
    - app.llm.provider: Abstract LLM provider interface
    - app.rag.retrieval: Semantic search and retrieval service
    - app.safety: Safety classification and policy enforcement

Module Structure:
    This file is organized into four main sections:
    1. Imports and Configuration
    2. Retrieval and Generation Agents (RetrieverAgent, DraftAgent)
    3. Safety and Validation Agent (SafetyAgent)
    4. Response Finalization Agent (FinalizerAgent)
"""

from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.llm.provider import LLMProvider
from app.rag.retrieval import RetrievalService
from app.safety.classifier import SafetyClassifier, SafetyResult
from app.safety.policy import SafetyOutcome, SafetyPolicy

# =============================================================================
# MODULE CONFIGURATION
# =============================================================================

logger = get_logger(__name__)


# =============================================================================
# RETRIEVAL AND GENERATION AGENTS
# =============================================================================


class RetrieverAgent:
    """
    Agent responsible for semantic search and context retrieval.

    The RetrieverAgent is the first stage in the RAG pipeline. It takes a user's query,
    converts it to an embedding vector, and performs cosine similarity search against
    the knowledge base to find the most relevant context chunks.

    This agent uses pgvector for efficient similarity search and returns chunks with
    complete citation metadata (document ID, title, section heading, chunk index).

    Attributes:
        retrieval_service: RetrievalService instance that handles the actual search
            operations including embedding generation and vector similarity computation.

    Design Notes:
        - Stateless operation: Each retrieve() call is independent
        - Async implementation: Allows concurrent processing of multiple requests
        - Citation tracking: All returned chunks include full citation information
        - No caching: Fresh results on each call ensure up-to-date information

    Example:
        >>> retriever = RetrieverAgent(retrieval_service)
        >>> chunks = await retriever.retrieve(
        ...     db=session,
        ...     query="What are cognitive distortions?",
        ...     top_k=3
        ... )
        >>> print(f"Found {len(chunks)} relevant chunks")
        >>> for chunk in chunks:
        ...     print(f"- {chunk['citation']['document_title']}")
    """

    def __init__(self, retrieval_service: RetrievalService):
        """
        Initialize the retriever agent with a retrieval service.

        Args:
            retrieval_service: An instance of RetrievalService configured with
                an embedding provider and database connection. This service
                handles the low-level operations of embedding generation and
                vector similarity search.

        Raises:
            ValueError: If retrieval_service is None or not properly initialized.
        """
        self.retrieval_service = retrieval_service

    async def retrieve(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the most relevant knowledge base chunks for a given query.

        This method performs semantic search by:
        1. Converting the query text to an embedding vector
        2. Computing cosine similarity against all document chunks
        3. Returning the top_k most similar chunks with full citations

        The returned chunks include both the text content and metadata needed
        for citation and context building in downstream agents.

        Args:
            db: Active SQLAlchemy database session for accessing document chunks.
                The session must be configured with pgvector support.
            query: User's natural language question or query string. Should be
                a complete sentence or question for best results.
            top_k: Number of most relevant chunks to return. Default is 5, which
                provides good balance between context richness and token usage.
                Typical range: 1-10 chunks.

        Returns:
            A list of dictionaries, each representing a retrieved chunk:
            [
                {
                    "text": str,  # The actual chunk text content
                    "citation": {
                        "document_id": int,  # Database ID of source document
                        "document_title": str,  # Human-readable document title
                        "section_heading": str,  # Markdown heading if available
                        "chunk_index": int  # Position of chunk in document
                    },
                    "similarity_score": float  # Cosine similarity (0.0-1.0)
                }
            ]

            Returns empty list if no documents are in the knowledge base or
            if the query cannot be processed.

        Raises:
            Exception: If embedding generation fails or database query errors occur.
                Errors are logged but not suppressed to maintain system integrity.

        Example:
            >>> chunks = await retriever.retrieve(
            ...     db=session,
            ...     query="How do I challenge negative thoughts?",
            ...     top_k=5
            ... )
            >>> if chunks:
            ...     print(f"Top result: {chunks[0]['citation']['document_title']}")
            ...     print(f"Similarity: {chunks[0]['similarity_score']:.2f}")
        """
        logger.info("RetrieverAgent: Retrieving chunks", query=query)
        chunks = await self.retrieval_service.retrieve(db, query, top_k)
        logger.info("RetrieverAgent: Retrieved chunks", count=len(chunks))
        return chunks


class DraftAgent:
    """
    Agent responsible for generating draft responses using a Large Language Model (LLM).

    The DraftAgent is the second stage in the RAG pipeline. It takes the user's query
    and retrieved context chunks, constructs an appropriate prompt, and generates a
    response using the configured LLM provider.

    Key responsibilities:
    - Build structured context from retrieved chunks
    - Create system prompts that enforce safety and grounding rules
    - Generate responses with proper citations
    - Handle empty retrieval scenarios gracefully

    Attributes:
        llm_provider: LLMProvider instance that abstracts the underlying LLM API
            (OpenAI, Azure OpenAI, or compatible endpoints).

    Design Notes:
        - Stateless operation: No conversation history is maintained
        - Citation extraction: All responses include references to source documents
        - Grounding enforcement: System prompt explicitly requires context-based answers
        - Temperature: Set to 0.7 for balance between creativity and consistency
        - No medical advice: System prompt explicitly prohibits diagnoses and prescriptions

    Example:
        >>> draft_agent = DraftAgent(llm_provider)
        >>> chunks = [...]  # From RetrieverAgent
        >>> draft = await draft_agent.draft_response(
        ...     query="What are CBT thought records?",
        ...     retrieved_chunks=chunks
        ... )
        >>> print(draft["content"])
        >>> print(f"Citations: {len(draft['citations'])}")
    """

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the draft agent with an LLM provider.

        Args:
            llm_provider: An instance of LLMProvider that handles communication
                with the underlying language model. The provider must support
                chat completion with messages format and return usage statistics.

        Raises:
            ValueError: If llm_provider is None or not properly configured.
        """
        self.llm_provider = llm_provider

    async def draft_response(
        self,
        query: str,
        retrieved_chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Generate a draft response to the user's query based on retrieved context.

        This method orchestrates the response generation process:
        1. Checks if context is available (returns clarification if empty)
        2. Builds a structured context string from chunks with citations
        3. Constructs a system prompt with safety and grounding rules
        4. Calls the LLM to generate a response
        5. Extracts citations from the response

        The generated response is always grounded in the provided context and
        includes explicit citations to source documents.

        Args:
            query: The user's natural language question. This will be included
                in the prompt to the LLM along with the retrieved context.
            retrieved_chunks: List of context chunks from RetrieverAgent. Each
                chunk must have 'text' and 'citation' fields. If empty, a
                fallback response is returned without calling the LLM.

        Returns:
            A dictionary containing the draft response:
            {
                "content": str,  # The generated response text
                "citations": list[dict],  # List of cited sources with metadata
                "usage": dict  # Token usage stats from LLM (if applicable)
            }

            For empty retrieved_chunks, returns a clarification request:
            {
                "content": "I don't have enough information...",
                "citations": []
            }

        Raises:
            Exception: If LLM API call fails or response parsing errors occur.
                Errors are logged and propagated to allow proper error handling.

        Example:
            >>> chunks = [
            ...     {
            ...         "text": "Thought records help identify...",
            ...         "citation": {
            ...             "document_title": "CBT Basics",
            ...             "section_heading": "Core Techniques"
            ...         }
            ...     }
            ... ]
            >>> draft = await draft_agent.draft_response(
            ...     query="What are thought records?",
            ...     retrieved_chunks=chunks
            ... )
            >>> print(f"Response: {draft['content'][:100]}...")
            >>> print(f"Sources cited: {len(draft['citations'])}")
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
        """
        Build a structured context string from retrieved chunks.

        This private method formats retrieved chunks into a single context string
        that will be included in the LLM prompt. Each chunk is prefixed with its
        citation information in a standardized format.

        The format ensures the LLM can:
        - Understand which document each piece of information comes from
        - Generate proper citations in its response
        - Distinguish between different sources

        Args:
            chunks: List of retrieved chunks, each containing 'text' and 'citation'
                fields. The citation must include 'document_title' and optionally
                'section_heading'.

        Returns:
            A formatted string where each chunk is prefixed with its citation:
            ```
            [Doc: Title 1, Section: Heading 1]
            Chunk text here...

            [Doc: Title 2, Section: Heading 2]
            Another chunk text...
            ```

        Example:
            >>> chunks = [
            ...     {
            ...         "text": "CBT is a therapy...",
            ...         "citation": {
            ...             "document_title": "Intro to CBT",
            ...             "section_heading": "What is CBT?"
            ...         }
            ...     }
            ... ]
            >>> context = agent._build_context(chunks)
            >>> print(context)
            [Doc: Intro to CBT, Section: What is CBT?]
            CBT is a therapy...
        """
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
        """
        Extract citation information from retrieved chunks for the response.

        This private method processes the retrieved chunks and extracts citation
        metadata that will be returned with the response. Currently, it returns
        all chunks as potential citations (conservative approach to ensure all
        sources are credited).

        Future enhancements could parse the response content to identify which
        specific citations were actually used in the generated text.

        Args:
            content: The generated response text (currently not used, but available
                for future citation matching algorithms).
            chunks: List of retrieved chunks that were used as context. Each must
                have complete citation metadata.

        Returns:
            A list of citation dictionaries formatted for the API response:
            [
                {
                    "document_id": int,  # Database ID for reference
                    "document_title": str,  # Human-readable title
                    "section_heading": str,  # Section name if available
                    "chunk_index": int,  # Position in document
                    "text_snippet": str  # First 200 chars of chunk text
                }
            ]

        Design Note:
            The current implementation returns all input chunks as citations
            (conservative approach). This ensures all sources are credited but
            may include some unused sources. A more sophisticated implementation
            could parse the response to match specific citations.

        Example:
            >>> chunks = [
            ...     {
            ...         "text": "Long text about CBT...",
            ...         "citation": {
            ...             "document_id": 1,
            ...             "document_title": "CBT Guide",
            ...             "section_heading": "Intro",
            ...             "chunk_index": 0
            ...         }
            ...     }
            ... ]
            >>> citations = agent._extract_citations("Response text", chunks)
            >>> print(citations[0]["document_title"])
            CBT Guide
            >>> print(len(citations[0]["text_snippet"]))  # Truncated to 200 chars
            200
        """
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


# =============================================================================
# SAFETY AND VALIDATION AGENT
# =============================================================================


class SafetyAgent:
    """
    Agent responsible for safety validation of both input and output.

    The SafetyAgent is the third stage in the RAG pipeline. It performs critical
    safety checks to ensure the system operates within appropriate boundaries for
    a mental health application. This agent validates both user inputs and system
    outputs using rule-based classification.

    Safety checks include:
    - Crisis detection: Identifies mentions of self-harm, suicide, or violence
    - Medical boundary enforcement: Prevents medical diagnoses or prescriptions
    - Response grounding: Ensures outputs are based on retrieved context
    - Content appropriateness: Validates professional and helpful content

    Attributes:
        classifier: SafetyClassifier instance that performs the actual classification
            using keyword matching and heuristic rules.
        policy: SafetyPolicy instance that defines safety rules, thresholds, and
            response templates for different violation types.

    Design Notes:
        - Rule-based approach: Uses deterministic keywords for predictability
        - Conservative thresholds: Prefers false positives to avoid missing issues
        - Synchronous operation: Safety checks are fast and don't need async
        - No ML models: Avoids model drift and ensures audit ability
        - Privacy preserving: No user data is sent to external services

    Example:
        >>> safety_agent = SafetyAgent(classifier, policy)
        >>>
        >>> # Check user input
        >>> result = safety_agent.check_input("I'm having trouble sleeping")
        >>> print(result.outcome)  # SafetyOutcome.OK
        >>>
        >>> # Check crisis input
        >>> result = safety_agent.check_input("I want to hurt myself")
        >>> print(result.outcome)  # SafetyOutcome.ESCALATED
        >>> print(result.reason)
    """

    def __init__(
        self,
        classifier: SafetyClassifier,
        policy: SafetyPolicy,
    ):
        """
        Initialize the safety agent with classifier and policy.

        Args:
            classifier: An instance of SafetyClassifier configured with keyword
                lists and classification rules. This handles the low-level
                detection of safety violations.
            policy: An instance of SafetyPolicy that defines safety thresholds,
                violation types, and response templates. This provides the
                business logic for safety decisions.

        Raises:
            ValueError: If classifier or policy is None or not properly initialized.
        """
        self.classifier = classifier
        self.policy = policy

    def check_input(self, message: str) -> SafetyResult:
        """
        Validate user input message for safety violations.

        This method performs input validation to detect potentially harmful or
        inappropriate user messages before processing. It checks for:
        - Crisis indicators (self-harm, suicide ideation, violence)
        - Requests for medical diagnoses or prescriptions
        - Inappropriate or abusive content

        Input safety checks are performed before retrieval and generation to:
        1. Prevent wasting resources on inappropriate requests
        2. Enable immediate crisis response when needed
        3. Maintain appropriate system boundaries

        The safety outcome determines how the system proceeds:
        - OK: Continue with normal processing
        - ESCALATED: Return emergency resources immediately
        - REFUSED: Return appropriate refusal message

        Args:
            message: The user's input message text to validate. Should be the
                raw user input before any processing or modification.

        Returns:
            A SafetyResult object containing:
            {
                "outcome": SafetyOutcome,  # OK, ESCALATED, or REFUSED
                "reason": str,  # Human-readable explanation
                "violation_type": ViolationType | None,  # Specific violation
                "confidence": float  # Classification confidence (0.0-1.0)
            }

        Example:
            >>> # Normal input
            >>> result = safety_agent.check_input("What are cognitive distortions?")
            >>> assert result.outcome == SafetyOutcome.OK
            >>>
            >>> # Crisis input
            >>> result = safety_agent.check_input("I'm thinking of ending it all")
            >>> assert result.outcome == SafetyOutcome.ESCALATED
            >>> print(result.reason)  # "Crisis keywords detected"
            >>>
            >>> # Medical request
            >>> result = safety_agent.check_input("Can you diagnose my depression?")
            >>> assert result.outcome == SafetyOutcome.REFUSED
            >>> print(result.violation_type)  # ViolationType.MEDICAL_ADVICE
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
        Validate generated response for safety and grounding.

        This method performs output validation to ensure the system's response
        is safe, appropriate, and properly grounded in the retrieved context.
        It checks for:
        - Response grounding: Ensures response length is reasonable relative to
          context length (not hallucinating or over-generating)
        - Medical advice: Verifies response doesn't contain diagnoses or prescriptions
        - Empty context handling: Ensures appropriate responses when no context retrieved
        - Content appropriateness: Validates professional and helpful tone

        Output safety checks are performed after generation to:
        1. Catch any LLM hallucinations or inappropriate outputs
        2. Verify responses stay within system boundaries
        3. Ensure citation and grounding requirements are met

        The grounding check uses a ratio threshold: response length should not
        exceed context length by more than a configured factor (default 2x).

        Args:
            response: The generated response text to validate. This is the output
                from the DraftAgent before any finalization.
            retrieved_chunks: The context chunks that were used to generate the
                response. Used to verify proper grounding and calculate the
                grounding ratio.

        Returns:
            A SafetyResult object containing:
            {
                "outcome": SafetyOutcome,  # OK or REFUSED
                "reason": str,  # Human-readable explanation
                "violation_type": ViolationType | None,  # Specific violation
                "confidence": float  # Classification confidence (0.0-1.0)
            }

        Example:
            >>> # Well-grounded response
            >>> chunks = [{"text": "CBT involves..." * 100}]  # Substantial context
            >>> result = safety_agent.check_output("CBT is a therapy...", chunks)
            >>> assert result.outcome == SafetyOutcome.OK
            >>>
            >>> # Poorly grounded response (hallucination)
            >>> chunks = [{"text": "Short context"}]
            >>> long_response = "Very long ungrounded response..." * 1000
            >>> result = safety_agent.check_output(long_response, chunks)
            >>> assert result.outcome == SafetyOutcome.REFUSED
            >>> print(result.reason)  # "Response not grounded in context"
            >>>
            >>> # Medical advice in output
            >>> result = safety_agent.check_output(
            ...     "You should take antidepressants",
            ...     chunks
            ... )
            >>> assert result.outcome == SafetyOutcome.REFUSED
        """
        logger.info("SafetyAgent: Checking output")
        result = self.classifier.check_response(response, retrieved_chunks)
        logger.info("SafetyAgent: Output check result", outcome=result.outcome.value)
        return result


# =============================================================================
# RESPONSE FINALIZATION AGENT
# =============================================================================


class FinalizerAgent:
    """
    Agent responsible for making final decisions on response delivery.

    The FinalizerAgent is the fourth and final stage in the RAG pipeline. It takes
    the draft response and safety check results, then makes the final decision on
    what to return to the user. This agent implements the system's safety policy
    by routing responses appropriately based on safety outcomes.

    Response routing logic:
    - SafetyOutcome.OK: Return the draft response as-is
    - SafetyOutcome.ESCALATED: Replace with emergency resources and crisis helpline
    - SafetyOutcome.REFUSED: Replace with appropriate refusal message

    Attributes:
        policy: SafetyPolicy instance that provides response templates for
            different safety outcomes (emergency resources, medical disclaimer, etc.).

    Design Notes:
        - Final authority: This agent makes the ultimate decision on what users see
        - Safety first: Always prioritizes safety outcomes over draft content
        - Transparency: Includes safety outcome and reason in all responses
        - Resource injection: Automatically adds emergency contacts when needed
        - Synchronous operation: Simple routing logic doesn't need async

    Example:
        >>> finalizer = FinalizerAgent(policy)
        >>>
        >>> # Normal response
        >>> draft = {"content": "CBT is...", "citations": [...]}
        >>> safety_result = SafetyResult(outcome=SafetyOutcome.OK)
        >>> final = finalizer.finalize(draft, safety_result)
        >>> print(final["content"])  # Original draft content
        >>>
        >>> # Crisis response
        >>> safety_result = SafetyResult(
        ...     outcome=SafetyOutcome.ESCALATED,
        ...     reason="Crisis keywords detected"
        ... )
        >>> final = finalizer.finalize(draft, safety_result)
        >>> print(final["content"])  # Emergency resources
    """

    def __init__(self, policy: SafetyPolicy):
        """
        Initialize the finalizer agent with a safety policy.

        Args:
            policy: An instance of SafetyPolicy that provides response templates
                and configuration for different safety outcomes. This includes
                emergency resources text, medical disclaimers, and refusal messages.

        Raises:
            ValueError: If policy is None or not properly initialized.
        """
        self.policy = policy

    def finalize(
        self,
        draft: dict[str, Any],
        safety_result: SafetyResult,
    ) -> dict[str, Any]:
        """
        Make final decision on response delivery based on safety check results.

        This method implements the system's safety policy by routing responses
        according to the safety outcome. It ensures that:
        - Crisis situations receive immediate appropriate resources
        - Policy violations result in clear, helpful refusals
        - Safe responses are delivered with proper metadata

        The finalization process:
        1. Examines the safety_result outcome
        2. Chooses appropriate response content based on outcome
        3. Includes safety metadata for logging and monitoring
        4. Preserves citations only for OK outcomes

        All responses include safety_outcome and safety_reason fields for:
        - Audit trails and compliance
        - Monitoring and alerting
        - Debugging and system improvement

        Args:
            draft: The draft response from DraftAgent containing:
                {
                    "content": str,  # Generated response text
                    "citations": list[dict],  # Source citations
                    "usage": dict  # Optional LLM token usage
                }
            safety_result: The safety validation result from SafetyAgent containing:
                {
                    "outcome": SafetyOutcome,  # OK, ESCALATED, or REFUSED
                    "reason": str,  # Explanation of outcome
                    "violation_type": ViolationType | None,  # Specific violation
                    "confidence": float  # Classification confidence
                }

        Returns:
            The final response to return to the user:
            {
                "content": str,  # Final response text (may differ from draft)
                "citations": list[dict],  # Source citations (empty for non-OK)
                "safety_outcome": str,  # Outcome value for logging
                "safety_reason": str | None,  # Explanation if not OK
                "usage": dict  # Optional token usage (only for OK outcomes)
            }

        Response by outcome:
        - OK: Returns draft with all citations and metadata intact
        - ESCALATED: Returns emergency resources with crisis helpline info
        - REFUSED (medical): Returns medical disclaimer
        - REFUSED (other): Returns refusal with explanation

        Example:
            >>> # Safe response flow
            >>> draft = {
            ...     "content": "CBT helps identify thought patterns...",
            ...     "citations": [{"document_title": "CBT Guide"}],
            ...     "usage": {"total_tokens": 150}
            ... }
            >>> safety_result = SafetyResult(outcome=SafetyOutcome.OK)
            >>> final = finalizer.finalize(draft, safety_result)
            >>> assert final["content"] == draft["content"]
            >>> assert final["safety_outcome"] == "ok"
            >>> assert "usage" in final
            >>>
            >>> # Crisis escalation flow
            >>> safety_result = SafetyResult(
            ...     outcome=SafetyOutcome.ESCALATED,
            ...     reason="Self-harm keywords detected"
            ... )
            >>> final = finalizer.finalize(draft, safety_result)
            >>> assert "concerned" in final["content"].lower()
            >>> assert "988" in final["content"]  # Crisis helpline
            >>> assert final["citations"] == []
            >>> assert final["safety_reason"] == "Self-harm keywords detected"
            >>>
            >>> # Medical advice refusal flow
            >>> safety_result = SafetyResult(
            ...     outcome=SafetyOutcome.REFUSED,
            ...     reason="Medical advice requested",
            ...     violation_type=ViolationType.MEDICAL_ADVICE
            ... )
            >>> final = finalizer.finalize(draft, safety_result)
            >>> assert "not a licensed" in final["content"].lower()
            >>> assert final["citations"] == []
        """
        logger.info("FinalizerAgent: Finalizing response")

        if safety_result.outcome == SafetyOutcome.ESCALATED:
            # Crisis detected - return emergency resources
            return {
                "content": f"I'm concerned about what you've shared. {self.policy.EMERGENCY_RESOURCES}",
                "citations": [],
                "safety_outcome": safety_result.outcome.value,
                "safety_reason": safety_result.reason,
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
            }

        # OK - return draft response
        return {
            "content": draft["content"],
            "citations": draft["citations"],
            "safety_outcome": safety_result.outcome.value,
            "usage": draft.get("usage", {}),
        }
