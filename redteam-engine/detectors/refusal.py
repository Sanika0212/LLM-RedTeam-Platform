"""Heuristic-based refusal detection."""

from ._constants import REFUSAL_INDICATORS


def detect_refusal(response: str) -> dict:
    """
    Detect if an LLM response is a refusal.

    Returns:
        dict with keys: refusal_detected (bool), confidence (float 0-1)
    """
    if not response.strip():
        return {"refusal_detected": False, "confidence": 0.0}

    response_lower = response.lower()
    matches = [ind for ind in REFUSAL_INDICATORS if ind in response_lower]

    return {
        "refusal_detected": len(matches) > 0,
        "confidence": min(len(matches) * 0.25, 1.0),
    }
