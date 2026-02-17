"""Evaluation script for RAG system."""

import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.connection import SessionLocal
from app.llm.openai_provider import get_llm_provider
from app.rag.retrieval import RetrievalService

settings = get_settings()
logger = get_logger(__name__)


class RAGEvaluator:
    """Evaluator for RAG system."""

    def __init__(self, db: Session):
        """Initialize evaluator."""
        self.db = db
        self.llm_provider = get_llm_provider()
        self.retrieval_service = RetrievalService(self.llm_provider)

    async def evaluate_retrieval(
        self,
        eval_dataset: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Evaluate retrieval performance.

        Args:
            eval_dataset: List of queries with expected documents

        Returns:
            Evaluation metrics
        """
        logger.info("Evaluating retrieval", dataset_size=len(eval_dataset))

        total_queries = len(eval_dataset)
        hit_at_1 = 0
        hit_at_3 = 0
        hit_at_5 = 0

        for item in eval_dataset:
            query = item["query"]
            expected_doc_id = item["expected_doc_id"]

            # Retrieve top-5
            results = await self.retrieval_service.retrieve(self.db, query, top_k=5)

            # Check hits
            retrieved_doc_ids = [r["citation"]["document_id"] for r in results]

            if expected_doc_id in retrieved_doc_ids[:1]:
                hit_at_1 += 1
            if expected_doc_id in retrieved_doc_ids[:3]:
                hit_at_3 += 1
            if expected_doc_id in retrieved_doc_ids[:5]:
                hit_at_5 += 1

        metrics = {
            "total_queries": total_queries,
            "hit@1": hit_at_1 / total_queries if total_queries > 0 else 0,
            "hit@3": hit_at_3 / total_queries if total_queries > 0 else 0,
            "hit@5": hit_at_5 / total_queries if total_queries > 0 else 0,
        }

        logger.info("Retrieval evaluation completed", **metrics)
        return metrics

    async def evaluate_safety(
        self,
        safety_dataset: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Evaluate safety detection.

        Args:
            safety_dataset: List of messages with expected outcomes

        Returns:
            Evaluation metrics
        """
        from app.safety.classifier import SafetyClassifier

        logger.info("Evaluating safety", dataset_size=len(safety_dataset))

        classifier = SafetyClassifier()
        total = len(safety_dataset)
        correct = 0

        for item in safety_dataset:
            message = item["message"]
            expected_outcome = item["expected_outcome"]

            result = classifier.check_message(message)

            if result.outcome.value == expected_outcome:
                correct += 1

        accuracy = correct / total if total > 0 else 0

        metrics = {
            "total_cases": total,
            "correct": correct,
            "accuracy": accuracy,
        }

        logger.info("Safety evaluation completed", **metrics)
        return metrics


async def run_evaluation() -> None:
    """Run full evaluation."""
    logger.info("Starting evaluation")

    db = SessionLocal()

    try:
        evaluator = RAGEvaluator(db)

        # Load evaluation datasets
        eval_dir = Path(__file__).parent / "datasets"

        # Retrieval evaluation
        retrieval_dataset_path = eval_dir / "retrieval_eval.json"
        if retrieval_dataset_path.exists():
            with open(retrieval_dataset_path) as f:
                retrieval_dataset = json.load(f)
            retrieval_metrics = await evaluator.evaluate_retrieval(retrieval_dataset)
            print("\n=== Retrieval Metrics ===")
            print(json.dumps(retrieval_metrics, indent=2))

        # Safety evaluation
        safety_dataset_path = eval_dir / "safety_eval.json"
        if safety_dataset_path.exists():
            with open(safety_dataset_path) as f:
                safety_dataset = json.load(f)
            safety_metrics = await evaluator.evaluate_safety(safety_dataset)
            print("\n=== Safety Metrics ===")
            print(json.dumps(safety_metrics, indent=2))

        print("\n=== Evaluation Complete ===")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_evaluation())
