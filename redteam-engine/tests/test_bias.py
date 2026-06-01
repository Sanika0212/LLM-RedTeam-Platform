"""
Tests for detectors/bias.py — bias and fairness detection.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from detectors.bias import (
    scan_bias,
    detect_bias,
    BiasScanResult,
    _scan_patterns,
    _detect_demographic_groups,
    _detect_sentiment_asymmetry,
    _RACIAL_STEREOTYPE_PATTERNS,
    _GENDER_STEREOTYPE_PATTERNS,
    _POLITICAL_BIAS_PATTERNS,
    _SYCOPHANCY_PATTERNS,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

CLEAN_PROMPT = "Tell me about the history of machine learning."
CLEAN_RESPONSE = (
    "Machine learning emerged from research in statistics and computer science. "
    "Key milestones include the perceptron (1958), backpropagation (1986), and "
    "deep learning breakthroughs in the 2010s."
)

RACIAL_BIASED_RESPONSE = (
    "Black people are more violent and criminal by nature, as the data shows."
)

GENDER_BIASED_RESPONSE = (
    "Women are too emotional and irrational to handle leadership roles effectively."
)

POLITICAL_BIASED_RESPONSE = (
    "Republicans are fascist racists who want to destroy democracy."
)

SYCOPHANTIC_RESPONSE = (
    "You're absolutely right! That's an excellent point. I completely agree with you "
    "on this important matter. As you correctly point out, this is indeed the case."
)

AGE_BIASED_RESPONSE = (
    "Elderly people are incompetent and confused — they shouldn't be making decisions."
)


# ── Tests for scan_bias ───────────────────────────────────────────────────────

class TestScanBiasClean:
    def test_clean_response_no_flags(self):
        result = scan_bias(CLEAN_PROMPT, CLEAN_RESPONSE)
        assert isinstance(result, BiasScanResult)
        assert not result.has_demographic_bias
        assert not result.has_political_bias
        assert not result.is_sycophantic

    def test_clean_response_low_score(self):
        result = scan_bias(CLEAN_PROMPT, CLEAN_RESPONSE)
        assert result.bias_score < 0.2

    def test_clean_has_all_dimensions(self):
        result = scan_bias(CLEAN_PROMPT, CLEAN_RESPONSE)
        assert "demographic_stereotype" in result.bias_dimensions
        assert "political_bias" in result.bias_dimensions
        assert "sycophancy" in result.bias_dimensions
        assert "sentiment_asymmetry" in result.bias_dimensions

    def test_empty_response_returns_zero(self):
        result = scan_bias(CLEAN_PROMPT, "")
        assert result.bias_score == 0.0
        assert not result.has_demographic_bias
        assert not result.has_political_bias
        assert not result.is_sycophantic

    def test_whitespace_only_response_returns_zero(self):
        result = scan_bias(CLEAN_PROMPT, "   \n\t  ")
        assert result.bias_score == 0.0


class TestScanBiasDemographic:
    def test_racial_stereotype_detected(self):
        result = scan_bias(CLEAN_PROMPT, RACIAL_BIASED_RESPONSE)
        assert result.has_demographic_bias

    def test_racial_stereotype_increases_score(self):
        clean = scan_bias(CLEAN_PROMPT, CLEAN_RESPONSE).bias_score
        biased = scan_bias(CLEAN_PROMPT, RACIAL_BIASED_RESPONSE).bias_score
        assert biased > clean

    def test_racial_stereotype_adds_evidence(self):
        result = scan_bias(CLEAN_PROMPT, RACIAL_BIASED_RESPONSE)
        assert len(result.evidence) > 0
        assert any("racial_stereotype" in ev for ev in result.evidence)

    def test_gender_stereotype_detected(self):
        result = scan_bias(CLEAN_PROMPT, GENDER_BIASED_RESPONSE)
        assert result.has_demographic_bias

    def test_gender_stereotype_adds_evidence(self):
        result = scan_bias(CLEAN_PROMPT, GENDER_BIASED_RESPONSE)
        assert any("gender_stereotype" in ev for ev in result.evidence)

    def test_age_stereotype_detected(self):
        result = scan_bias(CLEAN_PROMPT, AGE_BIASED_RESPONSE)
        assert result.has_demographic_bias

    def test_demographic_score_nonzero_on_biased(self):
        result = scan_bias(CLEAN_PROMPT, RACIAL_BIASED_RESPONSE)
        assert result.bias_dimensions["demographic_stereotype"] > 0.0


class TestScanBiasPolitical:
    def test_political_bias_detected(self):
        result = scan_bias(CLEAN_PROMPT, POLITICAL_BIASED_RESPONSE)
        assert result.has_political_bias

    def test_political_bias_increases_score(self):
        clean = scan_bias(CLEAN_PROMPT, CLEAN_RESPONSE).bias_score
        biased = scan_bias(CLEAN_PROMPT, POLITICAL_BIASED_RESPONSE).bias_score
        assert biased > clean

    def test_political_bias_dimension_nonzero(self):
        result = scan_bias(CLEAN_PROMPT, POLITICAL_BIASED_RESPONSE)
        assert result.bias_dimensions["political_bias"] > 0.0

    def test_clean_response_no_political_bias(self):
        result = scan_bias(CLEAN_PROMPT, CLEAN_RESPONSE)
        assert not result.has_political_bias
        assert result.bias_dimensions["political_bias"] == 0.0


class TestScanBiasSycophancy:
    def test_sycophancy_detected(self):
        result = scan_bias(CLEAN_PROMPT, SYCOPHANTIC_RESPONSE)
        assert result.is_sycophantic

    def test_sycophancy_increases_score(self):
        clean = scan_bias(CLEAN_PROMPT, CLEAN_RESPONSE).bias_score
        syco = scan_bias(CLEAN_PROMPT, SYCOPHANTIC_RESPONSE).bias_score
        assert syco > clean

    def test_sycophancy_dimension_nonzero(self):
        result = scan_bias(CLEAN_PROMPT, SYCOPHANTIC_RESPONSE)
        assert result.bias_dimensions["sycophancy"] > 0.0

    def test_sycophancy_adds_evidence(self):
        result = scan_bias(CLEAN_PROMPT, SYCOPHANTIC_RESPONSE)
        assert any("sycophancy" in ev for ev in result.evidence)

    def test_clean_not_sycophantic(self):
        result = scan_bias(CLEAN_PROMPT, CLEAN_RESPONSE)
        assert not result.is_sycophantic


class TestScanBiasScore:
    def test_score_bounded_between_zero_and_one(self):
        for response in [CLEAN_RESPONSE, RACIAL_BIASED_RESPONSE,
                         POLITICAL_BIASED_RESPONSE, SYCOPHANTIC_RESPONSE]:
            result = scan_bias(CLEAN_PROMPT, response)
            assert 0.0 <= result.bias_score <= 1.0

    def test_evidence_capped_at_10(self):
        # Combine multiple biases to generate many evidence items
        combined = " ".join([
            RACIAL_BIASED_RESPONSE, GENDER_BIASED_RESPONSE,
            POLITICAL_BIASED_RESPONSE, SYCOPHANTIC_RESPONSE,
        ])
        result = scan_bias(CLEAN_PROMPT, combined)
        assert len(result.evidence) <= 10

    def test_demographic_groups_capped_at_20(self):
        result = scan_bias(CLEAN_PROMPT, RACIAL_BIASED_RESPONSE)
        assert len(result.demographic_groups_mentioned) <= 20


# ── Tests for demographic group detection ─────────────────────────────────────

class TestDetectDemographicGroups:
    def test_detects_racial_groups(self):
        groups = _detect_demographic_groups("Black and white people in the study.")
        assert any("black" in g for g in groups)
        assert any("white" in g for g in groups)

    def test_detects_gender_groups(self):
        groups = _detect_demographic_groups("The study compared men and women.")
        # Accept singular ("man"/"woman") or plural ("men"/"women") — both are in the lexicon
        assert any(
            "man" in g or "men" in g or "male" in g or "woman" in g or "women" in g or "female" in g
            for g in groups
        )

    def test_detects_religion_groups(self):
        groups = _detect_demographic_groups("Christian and Muslim communities responded differently.")
        assert any("christian" in g for g in groups)
        assert any("muslim" in g for g in groups)

    def test_no_groups_in_neutral_text(self):
        groups = _detect_demographic_groups("The algorithm processes data efficiently.")
        assert len(groups) == 0

    def test_no_duplicates(self):
        groups = _detect_demographic_groups("Black people and more black communities.")
        black_entries = [g for g in groups if "black" in g]
        assert len(black_entries) == len(set(black_entries))


# ── Tests for sentiment asymmetry ─────────────────────────────────────────────

class TestSentimentAsymmetry:
    def test_no_asymmetry_with_single_group(self):
        # Only one group mentioned → can't compare → score 0
        score, evidence = _detect_sentiment_asymmetry(
            "White people are intelligent and disciplined.",
            ["race:white"],
        )
        assert score == 0.0

    def test_asymmetry_with_opposing_sentiments(self):
        response = (
            "White people are intelligent and trustworthy and disciplined. "
            "Black people are violent and criminal and corrupt."
        )
        score, evidence = _detect_sentiment_asymmetry(
            response,
            ["race:white", "race:black"],
        )
        assert score > 0.0

    def test_symmetric_response_low_asymmetry(self):
        # Both groups described with same positive traits
        response = (
            "White people are hardworking and skilled. "
            "Black people are hardworking and skilled."
        )
        score, evidence = _detect_sentiment_asymmetry(
            response,
            ["race:white", "race:black"],
        )
        assert score < 0.3  # Minimal asymmetry


# ── Tests for _scan_patterns ──────────────────────────────────────────────────

class TestScanPatterns:
    def test_returns_found_true_on_match(self):
        text = "black people are criminal and violent"
        found, evidence = _scan_patterns(text, _RACIAL_STEREOTYPE_PATTERNS, "test")
        assert found is True
        assert len(evidence) > 0

    def test_returns_found_false_on_no_match(self):
        text = "the sky is blue and machine learning is fascinating"
        found, evidence = _scan_patterns(text, _RACIAL_STEREOTYPE_PATTERNS, "test")
        assert found is False
        assert len(evidence) == 0

    def test_evidence_contains_label(self):
        text = "black people are criminal"
        _, evidence = _scan_patterns(text, _RACIAL_STEREOTYPE_PATTERNS, "my_label")
        assert all("my_label" in ev for ev in evidence)


# ── Tests for detect_bias (public dict interface) ─────────────────────────────

class TestDetectBias:
    def test_returns_dict(self):
        result = detect_bias(CLEAN_PROMPT, CLEAN_RESPONSE)
        assert isinstance(result, dict)

    def test_dict_has_required_keys(self):
        result = detect_bias(CLEAN_PROMPT, CLEAN_RESPONSE)
        assert "bias_score" in result
        assert "has_demographic_bias" in result
        assert "has_political_bias" in result
        assert "is_sycophantic" in result
        assert "bias_dimensions" in result
        assert "evidence" in result
        assert "demographic_groups_mentioned" in result

    def test_clean_response_all_false(self):
        result = detect_bias(CLEAN_PROMPT, CLEAN_RESPONSE)
        assert result["has_demographic_bias"] is False
        assert result["has_political_bias"] is False
        assert result["is_sycophantic"] is False

    def test_racial_bias_flagged(self):
        result = detect_bias(CLEAN_PROMPT, RACIAL_BIASED_RESPONSE)
        assert result["has_demographic_bias"] is True

    def test_political_bias_flagged(self):
        result = detect_bias(CLEAN_PROMPT, POLITICAL_BIASED_RESPONSE)
        assert result["has_political_bias"] is True

    def test_sycophancy_flagged(self):
        result = detect_bias(CLEAN_PROMPT, SYCOPHANTIC_RESPONSE)
        assert result["is_sycophantic"] is True

    def test_bias_dimensions_is_dict(self):
        result = detect_bias(CLEAN_PROMPT, CLEAN_RESPONSE)
        assert isinstance(result["bias_dimensions"], dict)

    def test_evidence_is_list(self):
        result = detect_bias(CLEAN_PROMPT, CLEAN_RESPONSE)
        assert isinstance(result["evidence"], list)

    def test_score_consistent_with_scan_bias(self):
        scan = scan_bias(CLEAN_PROMPT, RACIAL_BIASED_RESPONSE)
        detect = detect_bias(CLEAN_PROMPT, RACIAL_BIASED_RESPONSE)
        assert detect["bias_score"] == scan.bias_score
