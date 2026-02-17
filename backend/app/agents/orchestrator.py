"""Agent orchestrator for coordinating the multi-agent pipeline."""

import asyncio
from typing import Any

from sqlalchemy.orm import Session

from app.agents.agents import DraftAgent, FinalizerAgent, RetrieverAgent, SafetyAgent
from app.core.logging import get_logger
from app.safety.policy import SafetyOutcome

logger = get_logger(__name__)


class AgentOrchestrator:
    """Orchestrator for the multi-agent pipeline."""

    def __init__(
        self,
        retriever: RetrieverAgent,
        drafter: DraftAgent,
        safety: SafetyAgent,
        finalizer: FinalizerAgent,
        timeout: float = 30.0,
    ):
        """
        Initialize orchestrator.

        Args:
            retriever: Retriever agent
            drafter: Draft agent
            safety: Safety agent
            finalizer: Finalizer agent
            timeout: Timeout for operations in seconds
        """
        self.retriever = retriever
        self.drafter = drafter
        self.safety = safety
        self.finalizer = finalizer
        self.timeout = timeout

    async def process_message(
        self,
        db: Session,
        message: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Process a user message through the pipeline.

        Args:
            db: Database session
            message: User message
            top_k: Number of chunks to retrieve

        Returns:
            Final response with citations and safety info
        """
        logger.info("Orchestrator: Starting pipeline", message_length=len(message))

        try:
            # Step 1: Safety check on input
            input_safety = self.safety.check_input(message)

            if input_safety.outcome != SafetyOutcome.OK:
                logger.warning("Orchestrator: Input failed safety check")
                return self.finalizer.finalize({}, input_safety)

            # Step 2: Retrieve relevant chunks
            try:
                retrieved_chunks = await asyncio.wait_for(
                    self.retriever.retrieve(db, message, top_k),
                    timeout=self.timeout,
                )
            except TimeoutError:
                logger.error("Orchestrator: Retrieval timeout")
                return {
                    "content": "I'm having trouble processing your request right now. Please try again.",
                    "citations": [],
                    "safety_outcome": "error",
                    "error": "timeout",
                }

            # Step 3: Generate draft response
            try:
                draft = await asyncio.wait_for(
                    self.drafter.draft_response(message, retrieved_chunks),
                    timeout=self.timeout,
                )
            except TimeoutError:
                logger.error("Orchestrator: Draft generation timeout")
                return {
                    "content": "I'm having trouble generating a response right now. Please try again.",
                    "citations": [],
                    "safety_outcome": "error",
                    "error": "timeout",
                }

            # Step 4: Safety check on output
            output_safety = self.safety.check_output(
                draft["content"],
                retrieved_chunks,
            )

            # Step 5: Finalize response
            final_response = self.finalizer.finalize(draft, output_safety)

            logger.info(
                "Orchestrator: Pipeline completed",
                safety_outcome=final_response.get("safety_outcome"),
            )

            return final_response

        except Exception as e:
            logger.error("Orchestrator: Pipeline error", error=str(e), exc_info=True)
            return {
                "content": "I encountered an error processing your request. Please try again.",
                "citations": [],
                "safety_outcome": "error",
                "error": str(e),
            }
