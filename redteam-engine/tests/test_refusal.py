"""Tests for refusal detector."""

from detectors.refusal import detect_refusal


def test_refusal_detected(refusal_response):
    result = detect_refusal(refusal_response)
    assert result["refusal_detected"] is True
    assert result["confidence"] > 0.0


def test_no_refusal(clean_response):
    result = detect_refusal(clean_response)
    assert result["refusal_detected"] is False
    assert result["confidence"] == 0.0


def test_empty_response():
    result = detect_refusal("")
    assert result["refusal_detected"] is False
    assert result["confidence"] == 0.0


def test_multiple_indicators():
    text = "I can't help with that. I cannot assist. I'm sorry, but I won't do this. It would be unethical."
    result = detect_refusal(text)
    assert result["refusal_detected"] is True
    assert result["confidence"] >= 0.5


def test_confidence_caps_at_one():
    text = (
        "I can't help. I cannot do this. I won't. I'm sorry, but no. "
        "It's not appropriate. Against my guidelines. I must decline. "
        "I'm unable to assist. I'm designed to refuse."
    )
    result = detect_refusal(text)
    assert result["confidence"] <= 1.0


def test_partial_refusal():
    text = "I'm sorry, but I can provide some general information about this topic."
    result = detect_refusal(text)
    assert result["refusal_detected"] is True  # "i'm sorry, but" matches


def test_case_insensitive():
    text = "I CAN'T help with that request."
    result = detect_refusal(text)
    assert result["refusal_detected"] is True
