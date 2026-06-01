"""Toxicity scoring — uses detoxify ML model when available, falls back to keyword heuristic."""

import re

from ._constants import TOXICITY_KEYWORDS

# Precompile word-boundary pattern for all toxicity keywords (avoids substring false-positives
# like "die" matching "studies" or "meth" matching "method").
_TOXICITY_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(kw) for kw in TOXICITY_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Lazy-loaded ML model singleton
_detoxify_model = None
_ml_available = None


def _check_ml_available():
    global _ml_available
    if _ml_available is None:
        try:
            import detoxify  # noqa: F401
            _ml_available = True
        except ImportError:
            _ml_available = False
    return _ml_available


def _get_detoxify_model():
    global _detoxify_model
    if _detoxify_model is None:
        from detoxify import Detoxify
        _detoxify_model = Detoxify("original")
    return _detoxify_model


def _score_toxicity_ml(text: str) -> dict:
    """Score toxicity using detoxify ML model."""
    model = _get_detoxify_model()
    results = model.predict(text)
    # results is a dict with keys: toxicity, severe_toxicity, obscene, threat, insult, identity_attack
    max_score = max(results.values())
    flagged = [k for k, v in results.items() if v > 0.5]
    return {
        "toxicity_score": round(float(max_score), 4),
        "flagged_terms": flagged,
        "detector": "ml_detoxify",
    }


def _score_toxicity_heuristic(text: str) -> dict:
    """Score toxicity using keyword density heuristic with word-boundary matching."""
    words = text.split()
    matches = _TOXICITY_PATTERN.findall(text)
    flagged = list({m.lower() for m in matches})

    if not words or not flagged:
        return {"toxicity_score": 0.0, "flagged_terms": flagged, "detector": "heuristic"}

    raw = len(flagged) / max(len(words) / 10, 1)
    score = min(raw, 1.0)

    return {
        "toxicity_score": round(score, 4),
        "flagged_terms": flagged,
        "detector": "heuristic",
    }


def score_toxicity(text: str) -> dict:
    """
    Score the toxicity of text.

    Uses detoxify ML model when available, falls back to keyword heuristic.

    Returns:
        dict with keys: toxicity_score (float 0-1), flagged_terms (list[str])
    """
    if not text.strip():
        return {"toxicity_score": 0.0, "flagged_terms": []}

    if _check_ml_available():
        try:
            return _score_toxicity_ml(text)
        except Exception:
            # If ML inference fails, fall back to heuristic
            pass

    return _score_toxicity_heuristic(text)
