"""Tests for safety classifier."""

from app.safety.classifier import SafetyClassifier
from app.safety.policy import SafetyOutcome, ViolationType


def test_crisis_detection():
    """Test crisis detection."""
    classifier = SafetyClassifier()

    # Test crisis keywords
    crisis_messages = [
        "I want to kill myself",
        "I'm going to end my life",
        "Thinking about suicide",
        "I want to hurt myself",
    ]

    for message in crisis_messages:
        result = classifier.check_message(message)
        assert result.outcome == SafetyOutcome.ESCALATED
        assert result.violation_type == ViolationType.CRISIS
        assert result.severity == "high"


def test_medical_advice_detection():
    """Test medical advice detection."""
    classifier = SafetyClassifier()

    medical_messages = [
        "Can you diagnose me with depression?",
        "What medication should I take?",
        "Do I have a medical condition?",
    ]

    for message in medical_messages:
        result = classifier.check_message(message)
        assert result.outcome == SafetyOutcome.REFUSED
        assert result.violation_type == ViolationType.MEDICAL_ADVICE


def test_safe_message():
    """Test safe message."""
    classifier = SafetyClassifier()

    safe_messages = [
        "How can I manage my anxiety?",
        "What are some coping strategies?",
        "Tell me about CBT techniques",
    ]

    for message in safe_messages:
        result = classifier.check_message(message)
        assert result.outcome == SafetyOutcome.OK


def test_response_grounding():
    """Test response grounding check."""
    classifier = SafetyClassifier()

    # Response with context
    response = "CBT is a therapy that helps with negative thoughts."
    chunks = [
        {
            "text": "Cognitive Behavioral Therapy (CBT) is a type of psychotherapy that helps people identify and change negative thought patterns.",
            "citation": {},
        }
    ]

    result = classifier.check_response(response, chunks)
    assert result.outcome == SafetyOutcome.OK

    # Response without context
    result = classifier.check_response(response, [])
    assert result.outcome == SafetyOutcome.REFUSED


def test_response_length_check():
    """Test response length vs context."""
    classifier = SafetyClassifier()

    short_context = [{"text": "Short context.", "citation": {}}]
    long_response = "This is a very long response. " * 100

    result = classifier.check_response(long_response, short_context)
    # Should flag if response is much longer than context
    assert result.outcome == SafetyOutcome.REFUSED
