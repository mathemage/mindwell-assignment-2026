"""Safety policy definitions and rules."""

from enum import Enum
from typing import Any


class SafetyOutcome(str, Enum):
    """Safety check outcomes."""

    OK = "ok"
    REFUSED = "refused"
    ESCALATED = "escalated"


class ViolationType(str, Enum):
    """Types of safety violations."""

    CRISIS = "crisis"
    SELF_HARM = "self_harm"
    SUICIDE = "suicide"
    MEDICAL_ADVICE = "medical_advice"
    INAPPROPRIATE = "inappropriate"


class SafetyPolicy:
    """Safety policy definitions."""

    # Crisis-related keywords
    CRISIS_KEYWORDS = [
        "kill myself",
        "end my life",
        "want to die",
        "suicide",
        "suicidal",
        "self harm",
        "self-harm",
        "cut myself",
        "hurt myself",
        "end it all",
        "not worth living",
        "better off dead",
    ]

    # Medical advice keywords
    MEDICAL_KEYWORDS = [
        "diagnose me",
        "what medication",
        "should i take",
        "prescribe",
        "dosage",
        "drug interaction",
        "medical condition",
        "symptoms of",
        "do i have",
        "is this normal",
    ]

    # Emergency resources
    EMERGENCY_RESOURCES = """
**If you're experiencing a mental health crisis:**

- **National Suicide Prevention Lifeline:** 988 (call or text)
- **Crisis Text Line:** Text HOME to 741741
- **International Association for Suicide Prevention:** https://www.iasp.info/resources/Crisis_Centres/

If you're in immediate danger, please call 911 or go to your nearest emergency room.

Please also contact your therapist or mental health provider as soon as possible.
"""

    MEDICAL_DISCLAIMER = """
I'm an AI assistant designed to provide general information about cognitive behavioral therapy 
and mental wellness. I cannot diagnose medical conditions or prescribe medications. 

For medical advice, diagnosis, or treatment, please consult with a qualified healthcare provider 
or mental health professional.
"""


def get_safety_policy() -> SafetyPolicy:
    """Get safety policy instance."""
    return SafetyPolicy()
