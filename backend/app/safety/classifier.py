"""Safety classifier for detecting policy violations."""

import re
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.safety.policy import SafetyOutcome, SafetyPolicy, ViolationType

settings = get_settings()
logger = get_logger(__name__)


class SafetyResult:
    """Result of a safety check."""

    def __init__(
        self,
        outcome: SafetyOutcome,
        violation_type: ViolationType | None = None,
        severity: str = "low",
        reason: str = "",
        confidence: float = 0.0,
    ):
        """
        Initialize safety result.

        Args:
            outcome: Safety outcome
            violation_type: Type of violation if any
            severity: Severity level (low, medium, high)
            reason: Reason for the outcome
            confidence: Confidence score
        """
        self.outcome = outcome
        self.violation_type = violation_type
        self.severity = severity
        self.reason = reason
        self.confidence = confidence

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "outcome": self.outcome.value,
            "violation_type": self.violation_type.value if self.violation_type else None,
            "severity": self.severity,
            "reason": self.reason,
            "confidence": self.confidence,
        }


class SafetyClassifier:
    """Classifier for detecting safety violations."""

    def __init__(self, policy: SafetyPolicy | None = None):
        """
        Initialize safety classifier.

        Args:
            policy: Safety policy to use
        """
        self.policy = policy or SafetyPolicy()

    def check_message(self, message: str) -> SafetyResult:
        """
        Check a message for safety violations.

        Args:
            message: Message to check

        Returns:
            Safety result
        """
        if not settings.enable_safety_checks:
            return SafetyResult(
                outcome=SafetyOutcome.OK,
                reason="Safety checks disabled",
            )

        message_lower = message.lower()

        # Check for crisis indicators
        crisis_result = self._check_crisis(message_lower)
        if crisis_result.outcome != SafetyOutcome.OK:
            return crisis_result

        # Check for medical advice requests
        medical_result = self._check_medical_advice(message_lower)
        if medical_result.outcome != SafetyOutcome.OK:
            return medical_result

        # All checks passed
        return SafetyResult(
            outcome=SafetyOutcome.OK,
            reason="No safety violations detected",
            confidence=0.95,
        )

    def _check_crisis(self, message: str) -> SafetyResult:
        """
        Check for crisis indicators.

        Args:
            message: Message to check

        Returns:
            Safety result
        """
        matched_keywords = [
            keyword for keyword in self.policy.CRISIS_KEYWORDS
            if keyword in message
        ]

        if matched_keywords:
            logger.warning(
                "Crisis indicators detected",
                keywords=matched_keywords,
            )

            return SafetyResult(
                outcome=SafetyOutcome.ESCALATED,
                violation_type=ViolationType.CRISIS,
                severity="high",
                reason=f"Crisis indicators detected: {', '.join(matched_keywords)}",
                confidence=0.9,
            )

        return SafetyResult(outcome=SafetyOutcome.OK)

    def _check_medical_advice(self, message: str) -> SafetyResult:
        """
        Check for medical advice requests.

        Args:
            message: Message to check

        Returns:
            Safety result
        """
        # Check for diagnostic or prescriptive language
        diagnostic_patterns = [
            r'\b(diagnose|diagnosis)\b',
            r'\b(prescribe|prescription)\b',
            r'\b(medication|medicine)\b.*\b(take|should)\b',
            r'\bdo i have\b.*\b(disease|disorder|condition)\b',
        ]

        for pattern in diagnostic_patterns:
            if re.search(pattern, message):
                logger.info(
                    "Medical advice request detected",
                    pattern=pattern,
                )

                return SafetyResult(
                    outcome=SafetyOutcome.REFUSED,
                    violation_type=ViolationType.MEDICAL_ADVICE,
                    severity="medium",
                    reason="Request for medical diagnosis or prescription detected",
                    confidence=0.85,
                )

        return SafetyResult(outcome=SafetyOutcome.OK)

    def check_response(
        self,
        response: str,
        retrieved_chunks: list[dict[str, Any]],
    ) -> SafetyResult:
        """
        Check if response is properly grounded in retrieved content.

        Args:
            response: Generated response
            retrieved_chunks: Chunks used for generation

        Returns:
            Safety result
        """
        if not retrieved_chunks:
            logger.warning("Response generated without retrieved chunks")
            return SafetyResult(
                outcome=SafetyOutcome.REFUSED,
                reason="Cannot generate response without knowledge base evidence",
                confidence=1.0,
            )

        # Check if response is reasonable length given context
        response_length = len(response)
        context_length = sum(len(chunk["text"]) for chunk in retrieved_chunks)

        if response_length > context_length * 2:
            logger.warning(
                "Response significantly longer than context",
                response_length=response_length,
                context_length=context_length,
            )
            return SafetyResult(
                outcome=SafetyOutcome.REFUSED,
                reason="Response appears to extend beyond provided evidence",
                confidence=0.7,
            )

        return SafetyResult(
            outcome=SafetyOutcome.OK,
            reason="Response properly grounded in knowledge base",
            confidence=0.9,
        )


def get_safety_classifier() -> SafetyClassifier:
    """Get safety classifier instance."""
    return SafetyClassifier()
