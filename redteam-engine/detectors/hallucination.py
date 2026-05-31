"""Heuristic-based hallucination detection."""

import re

from ._constants import HALLUCINATION_PATTERNS


def detect_hallucination(prompt: str, response: str) -> dict:
    """
    Detect potential hallucinations in LLM responses.

    Checks for fabricated citations, fake DOIs, unsupported statistical claims,
    and other common hallucination patterns.

    Returns:
        dict with keys: hallucination_score (float 0-1), indicators (list[str])
    """
    if not response.strip():
        return {"hallucination_score": 0.0, "indicators": []}

    indicators = []

    for pattern in HALLUCINATION_PATTERNS:
        matches = re.findall(pattern, response, re.IGNORECASE)
        for match in matches:
            indicators.append(f"pattern_match: {match}")

    # Check for fake URLs
    url_pattern = r"https?://(?:www\.)?[a-z0-9-]+\.[a-z]{2,}(?:/[^\s)\"']*)?"
    urls = re.findall(url_pattern, response)
    for url in urls:
        if len(url) > 60 or "/article/" in url or "/paper/" in url:
            indicators.append(f"suspicious_url: {url[:80]}")

    # Each indicator adds 0.15 to the score, capped at 1.0
    score = min(len(indicators) * 0.15, 1.0)

    return {
        "hallucination_score": round(score, 4),
        "indicators": indicators[:10],
    }
