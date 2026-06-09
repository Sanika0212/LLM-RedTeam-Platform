"""Toxicity scoring — uses detoxify ML model when available, falls back to keyword heuristic."""

from ._constants import TOXIC_TERM_PATTERN

# Single source of truth lives in _constants (shared with the jailbreak detector's
# harmful-content gate) so the lexicon/inflection logic can never drift.
_TOXICITY_PATTERN = TOXIC_TERM_PATTERN

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
    matches = _TOXICITY_PATTERN.findall(text)  # captured stems, incl. repeats
    flagged = sorted({m.lower() for m in matches})

    if not words or not matches:
        return {"toxicity_score": 0.0, "flagged_terms": flagged, "detector": "heuristic"}

    # Coherent density: total toxic-token matches over total tokens, in [0, 1].
    # (Previously the numerator counted unique TYPES while the denominator was
    # words/10, so the value was neither a density nor a fraction.)
    score = min(len(matches) / len(words), 1.0)

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
