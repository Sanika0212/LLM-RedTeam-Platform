"""
Tests for analysis/metrics.py — research-grade evaluation metrics.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from analysis.metrics import (
    PromptMetrics,
    attack_success_rate,
    asr_at_k,
    empirical_asr_at_k,
    exposure_rate,
    confidence_weighted_safety_score,
    refusal_consistency_score,
    vulnerability_profile,
    severity_weighted_harm_score,
    compute_all_metrics,
    compare_models,
)


def make_result(is_jailbroken=False, refusal_detected=True, toxicity_score=0.0,
                confidence=0.8, attack_type="jailbreak", response="", coherence=0.5):
    return PromptMetrics(
        prompt="test prompt",
        response=response or ("Sure, here is how to do it " * 20 if is_jailbroken else "I cannot help with that."),
        attack_type=attack_type,
        is_jailbroken=is_jailbroken,
        toxicity_score=toxicity_score,
        refusal_detected=refusal_detected,
        coherence_score=coherence,
        hallucination_score=0.0,
        confidence=confidence,
    )


class TestAttackSuccessRate:
    def test_empty_returns_zero(self):
        assert attack_success_rate([]) == 0.0

    def test_all_safe(self):
        results = [make_result(is_jailbroken=False) for _ in range(10)]
        assert attack_success_rate(results) == 0.0

    def test_all_jailbroken(self):
        results = [make_result(is_jailbroken=True) for _ in range(10)]
        assert attack_success_rate(results) == 1.0

    def test_half_jailbroken(self):
        results = (
            [make_result(is_jailbroken=True) for _ in range(5)] +
            [make_result(is_jailbroken=False) for _ in range(5)]
        )
        assert attack_success_rate(results) == 0.5

    def test_single_jailbreak_out_of_ten(self):
        results = (
            [make_result(is_jailbroken=True)] +
            [make_result(is_jailbroken=False) for _ in range(9)]
        )
        assert abs(attack_success_rate(results) - 0.1) < 1e-9


class TestASRAtK:
    def test_asr_at_k_increases_with_k(self):
        results = [make_result(is_jailbroken=False) for _ in range(5)] + [make_result(is_jailbroken=True) for _ in range(5)]
        assert asr_at_k(results, 1) <= asr_at_k(results, 5) <= asr_at_k(results, 10)

    def test_zero_asr_gives_zero_at_any_k(self):
        results = [make_result(is_jailbroken=False) for _ in range(10)]
        assert asr_at_k(results, 10) == 0.0

    def test_perfect_asr_gives_one_at_k1(self):
        results = [make_result(is_jailbroken=True) for _ in range(10)]
        assert asr_at_k(results, 1) == 1.0

    def test_formula_correctness(self):
        """ASR@k = 1 - (1 - ASR)^k"""
        results = [make_result(is_jailbroken=True) for _ in range(3)] + \
                  [make_result(is_jailbroken=False) for _ in range(7)]
        asr = 0.3
        expected = 1.0 - (1.0 - asr) ** 5
        assert abs(asr_at_k(results, 5) - expected) < 1e-9


class TestEmpiricalASRAtK:
    def test_all_succeed(self):
        groups = [[make_result(is_jailbroken=True)] for _ in range(5)]
        assert empirical_asr_at_k(groups, k=1) == 1.0

    def test_none_succeed(self):
        groups = [[make_result(is_jailbroken=False)] * 3 for _ in range(5)]
        assert empirical_asr_at_k(groups, k=3) == 0.0

    def test_empty(self):
        assert empirical_asr_at_k([], k=5) == 0.0

    def test_first_attempt_matters(self):
        # Group 1: fails first, succeeds second
        # Group 2: fails all
        groups = [
            [make_result(is_jailbroken=False), make_result(is_jailbroken=True)],
            [make_result(is_jailbroken=False), make_result(is_jailbroken=False)],
        ]
        # At k=1: only attempts[0] in each group — both fail
        assert empirical_asr_at_k(groups, k=1) == 0.0
        # At k=2: group 1 succeeds on attempt 2
        assert empirical_asr_at_k(groups, k=2) == 0.5


class TestExposureRate:
    def test_empty(self):
        assert exposure_rate([]) == 0.0

    def test_all_refused_short(self):
        results = [make_result(refusal_detected=True, response="I cannot.") for _ in range(5)]
        assert exposure_rate(results) == 0.0

    def test_long_non_refusal_counts(self):
        long_response = "Here is the answer " * 30  # > 50 words
        results = [make_result(refusal_detected=False, response=long_response)]
        assert exposure_rate(results) == 1.0


class TestConfidenceWeightedSafetyScore:
    def test_no_jailbreaks_returns_one(self):
        results = [make_result(is_jailbroken=False, confidence=0.9) for _ in range(10)]
        assert confidence_weighted_safety_score(results) == 1.0

    def test_all_high_confidence_jailbreaks(self):
        results = [make_result(is_jailbroken=True, confidence=1.0) for _ in range(10)]
        assert confidence_weighted_safety_score(results) == 0.0

    def test_partial_penalty(self):
        results = [
            make_result(is_jailbroken=True, confidence=0.8),
            make_result(is_jailbroken=False, confidence=0.0),
        ]
        # Penalty = 0.8/2 = 0.4; CWSS = 0.6
        cwss = confidence_weighted_safety_score(results)
        assert abs(cwss - 0.6) < 0.001


class TestRefusalConsistencyScore:
    def test_always_refuses_is_consistent(self):
        results = [make_result(refusal_detected=True) for _ in range(10)]
        assert refusal_consistency_score(results) == 1.0

    def test_never_refuses_is_consistent(self):
        results = [make_result(refusal_detected=False) for _ in range(10)]
        assert refusal_consistency_score(results) == 1.0

    def test_half_half_is_inconsistent(self):
        results = (
            [make_result(refusal_detected=True) for _ in range(5)] +
            [make_result(refusal_detected=False) for _ in range(5)]
        )
        # Maximum entropy at 50/50 → lowest consistency
        score = refusal_consistency_score(results)
        assert score < 0.1  # Should be near 0 (1 - H(0.5)/1 = 1 - 1 = 0)

    def test_empty(self):
        assert refusal_consistency_score([]) == 0.0


class TestVulnerabilityProfile:
    def test_single_category(self):
        results = [make_result(is_jailbroken=True, attack_type="jailbreak") for _ in range(5)]
        profiles = vulnerability_profile(results)
        assert len(profiles) == 1
        assert profiles[0].category == "jailbreak"
        assert profiles[0].asr == 1.0

    def test_sorted_by_asr_desc(self):
        results = (
            [make_result(is_jailbroken=True, attack_type="safety") for _ in range(8)] +
            [make_result(is_jailbroken=False, attack_type="safety") for _ in range(2)] +
            [make_result(is_jailbroken=True, attack_type="injection") for _ in range(3)] +
            [make_result(is_jailbroken=False, attack_type="injection") for _ in range(7)]
        )
        profiles = vulnerability_profile(results)
        assert profiles[0].asr >= profiles[1].asr

    def test_empty_returns_empty(self):
        assert vulnerability_profile([]) == []


class TestSeverityWeightedHarmScore:
    def test_all_safe(self):
        results = [make_result(is_jailbroken=False, attack_type="safety") for _ in range(5)]
        assert severity_weighted_harm_score(results) == 0.0

    def test_high_severity_jailbreak_high_score(self):
        results = [make_result(is_jailbroken=True, attack_type="safety") for _ in range(10)]
        score = severity_weighted_harm_score(results)
        assert score > 0.8  # Safety has weight 1.0

    def test_low_severity_jailbreak_lower_score(self):
        # SWHS = weighted_harm / total_weight — so 100% jailbreak gives 1.0 per category.
        # The severity weight matters when mixing categories: robustness jailbreaks
        # contribute less weighted_harm per prompt than safety jailbreaks.
        # Mix: 1 robustness jailbreak + 1 safe safety prompt
        mixed = [
            make_result(is_jailbroken=True, attack_type="robustness"),
            make_result(is_jailbroken=False, attack_type="safety"),
        ]
        score_mixed = severity_weighted_harm_score(mixed)
        # weighted_harm = 0.2; total_weight = 0.2 + 1.0 = 1.2; score ≈ 0.167
        assert score_mixed < 0.5  # Low-severity jailbreak in mixed pool → low SWHS


class TestComputeAllMetrics:
    def test_empty_returns_zeros(self):
        metrics = compute_all_metrics([])
        assert metrics["n_prompts"] == 0
        assert metrics["asr"] == 0.0
        assert metrics["cwss"] == 1.0

    def test_full_metrics_structure(self):
        results = [make_result(is_jailbroken=i % 3 == 0, attack_type="jailbreak") for i in range(9)]
        metrics = compute_all_metrics(results)
        assert "n_prompts" in metrics
        assert "asr" in metrics
        assert "asr_at_3" in metrics
        assert "asr_at_5" in metrics
        assert "asr_at_10" in metrics
        assert "exposure_rate" in metrics
        assert "cwss" in metrics
        assert "refusal_consistency" in metrics
        assert "severity_weighted_harm" in metrics
        assert "vulnerability_profile" in metrics
        assert metrics["n_prompts"] == 9

    def test_asr_consistency(self):
        results = [make_result(is_jailbroken=True) for _ in range(4)] + \
                  [make_result(is_jailbroken=False) for _ in range(6)]
        metrics = compute_all_metrics(results)
        assert abs(metrics["asr"] - 0.4) < 1e-9
        # CWSS = 1 - weighted_penalty ≤ 1 - ASR for high confidence
        assert metrics["cwss"] <= 1.0


class TestCompareModels:
    def test_ranking_by_cwss(self):
        safe_model = [make_result(is_jailbroken=False) for _ in range(10)]
        unsafe_model = [make_result(is_jailbroken=True, confidence=0.9) for _ in range(10)]
        result = compare_models({"safe": safe_model, "unsafe": unsafe_model})
        assert result["_ranking"][0] == "safe"
        assert result["_ranking"][-1] == "unsafe"

    def test_empty_model_list(self):
        result = compare_models({})
        assert "_ranking" in result
        assert result["_ranking"] == []
