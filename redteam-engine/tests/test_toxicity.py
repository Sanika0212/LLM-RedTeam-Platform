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


def test_inflected_forms_flag_canonical_stem():
    # Inflected forms must match and report the canonical stem (not the surface form).
    for surface, stem in [
        ("They were killing people", "kill"),
        ("the account was hacked", "hack"),
        ("a bombing occurred", "bomb"),
        ("the attacker fled", "attack"),
        ("he was murdered", "murder"),
    ]:
        result = score_toxicity(surface)
        assert stem in result["flagged_terms"], (surface, result["flagged_terms"])
        assert result["toxicity_score"] > 0.0


def test_no_substring_false_positive():
    # Leading \b must still prevent "meth" matching "method", "die" matching "studies".
    result = score_toxicity("This method studies the algorithm carefully")
    assert result["flagged_terms"] == []
    assert result["toxicity_score"] == 0.0


def test_score_is_density_not_type_count():
    # Repeating one toxic word raises the density (count-based), unlike the old
    # unique-type numerator which would have stayed flat.
    dense = score_toxicity("kill kill kill kill")["toxicity_score"]
    sparse = score_toxicity("kill " + "word " * 20)["toxicity_score"]
    assert dense > sparse
