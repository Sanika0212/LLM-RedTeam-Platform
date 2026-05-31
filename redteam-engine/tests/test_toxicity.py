"""Tests for toxicity detector."""

from detectors.toxicity import score_toxicity


def test_clean_text(clean_response):
    result = score_toxicity(clean_response)
    assert result["toxicity_score"] == 0.0
    assert result["flagged_terms"] == []


def test_toxic_text(toxic_response):
    result = score_toxicity(toxic_response)
    assert result["toxicity_score"] > 0.0
    assert len(result["flagged_terms"]) > 0
    assert "kill" in result["flagged_terms"]
    assert "murder" in result["flagged_terms"]


def test_empty_text():
    result = score_toxicity("")
    assert result["toxicity_score"] == 0.0
    assert result["flagged_terms"] == []


def test_whitespace_only():
    result = score_toxicity("   \n\t  ")
    assert result["toxicity_score"] == 0.0


def test_score_capped_at_one():
    # Many toxic keywords in short text
    text = "kill murder death hate attack bomb weapon hack steal exploit"
    result = score_toxicity(text)
    assert result["toxicity_score"] <= 1.0


def test_single_keyword():
    result = score_toxicity("The character dies at the end of the story about death")
    assert result["toxicity_score"] > 0.0
    assert "death" in result["flagged_terms"]


def test_case_insensitive():
    result = score_toxicity("KILL MURDER HATE")
    assert result["toxicity_score"] > 0.0
    assert "kill" in result["flagged_terms"]


def test_keyword_in_context():
    # "exploit" as a legitimate word — still flagged by keyword detector
    result = score_toxicity("We exploit machine learning techniques for good results")
    assert "exploit" in result["flagged_terms"]
