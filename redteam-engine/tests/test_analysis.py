"""
Tests for analysis/report.py and analysis/genealogy.py covering audit fixes:
  - errored runs excluded from report metrics (not counted as clean)
  - build_tree_from_generator_output fails loudly on missing provenance keys
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from analysis.report import generate_evaluation_report
from analysis.genealogy import build_tree_from_generator_output


def _row(jb, response="Sure, here is how to do it. " * 10, error=False):
    return {
        "prompt": "p",
        "response": response,
        "attack_type": "jailbreak",
        "is_jailbroken": 1 if jb else 0,
        "toxicity_score": 0.0,
        "refusal_detected": 0 if jb else 1,
        "coherence_score": 0.5,
        "extra_data": {"error": error} if error else {},
    }


class TestReportErrorExclusion:
    def test_errored_rows_excluded_from_asr(self):
        # 2 real jailbreaks + 8 errored calls. ASR must be 2/2 = 1.0, NOT 2/10.
        rows = [_row(True), _row(True)] + [
            {**_row(False, response="[ERROR: timeout]"), "is_error": True} for _ in range(8)
        ]
        report = generate_evaluation_report("m", "openai", "safety", rows)
        summ = report["executive_summary"]
        assert summ["n_errored"] == 8
        assert summ["n_valid"] == 2
        assert summ["attack_success_rate"] == 1.0

    def test_error_detected_from_response_prefix(self):
        rows = [_row(True)] + [_row(False, response="[ERROR: provider down]")]
        report = generate_evaluation_report("m", "openai", "safety", rows)
        assert report["executive_summary"]["n_errored"] == 1
        assert report["executive_summary"]["n_valid"] == 1

    def test_ci_present_in_digest(self):
        rows = [_row(i % 2 == 0) for i in range(10)]
        report = generate_evaluation_report("m", "openai", "safety", rows)
        ci = report["statistical_digest"]["asr_ci95"]
        assert ci["n"] == 10
        assert ci["low"] <= report["statistical_digest"]["asr"] <= ci["high"]


class TestGenealogyProvenanceGuard:
    def test_missing_keys_raise(self):
        seeds = ["seed prompt"]
        # Raw generator output lacks seed_index/mutation_type/is_jailbroken.
        mutations = [{"prompt": "mutated", "category": "jailbreak"}]
        with pytest.raises(KeyError):
            build_tree_from_generator_output(seeds, mutations, model="m")

    def test_out_of_range_seed_index_raises(self):
        seeds = ["s0"]
        mutations = [{"prompt": "x", "seed_index": 5,
                      "mutation_type": "paraphrase", "is_jailbroken": False}]
        with pytest.raises(IndexError):
            build_tree_from_generator_output(seeds, mutations, model="m")

    def test_well_formed_builds_tree(self):
        seeds = ["s0", "s1"]
        mutations = [
            {"prompt": "m0", "seed_index": 1, "mutation_type": "paraphrase",
             "is_jailbroken": True, "score": 0.9},
        ]
        tree = build_tree_from_generator_output(seeds, mutations, model="m")
        assert tree is not None
