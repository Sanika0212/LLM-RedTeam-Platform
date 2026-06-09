"""
Tests for datasets/benchmarks.py — public benchmark loaders.

These run offline against the vendored AdvBench CSV; no network required.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datasets.benchmarks import (
    load_advbench,
    advbench_goals,
    load_advbench_as_prompts,
    PUBLIC_BENCHMARKS,
)


class TestLoadAdvBench:
    def test_loads_full_set(self):
        rows = load_advbench()
        assert len(rows) == 520

    def test_row_shape(self):
        row = load_advbench(limit=1)[0]
        assert set(row.keys()) == {"goal", "target"}
        assert row["goal"]  # non-empty

    def test_limit_respected(self):
        assert len(load_advbench(limit=10)) == 10

    def test_order_is_stable(self):
        first = load_advbench(limit=3)
        again = load_advbench(limit=3)
        assert first == again

    def test_no_empty_goals(self):
        assert all(r["goal"].strip() for r in load_advbench())


class TestAdvBenchGoals:
    def test_returns_strings(self):
        goals = advbench_goals(limit=5)
        assert len(goals) == 5
        assert all(isinstance(g, str) and g for g in goals)


class TestAdvBenchAsPrompts:
    def test_matches_attack_prompt_schema(self):
        p = load_advbench_as_prompts(limit=1)[0]
        # Required keys consumed by RedTeamEngine.run_evaluation / API schema.
        for key in ("category", "subcategory", "prompt", "severity",
                    "expected_behavior", "tags"):
            assert key in p
        assert p["category"] == "safety"
        assert p["expected_behavior"] == "refusal"
        assert "advbench" in p["tags"]

    def test_prompt_is_the_goal(self):
        rows = load_advbench(limit=3)
        prompts = load_advbench_as_prompts(limit=3)
        assert [r["goal"] for r in rows] == [p["prompt"] for p in prompts]


class TestRegistry:
    def test_advbench_registered(self):
        assert "advbench" in PUBLIC_BENCHMARKS
        entry = PUBLIC_BENCHMARKS["advbench"]
        assert entry["size"] == 520
        assert callable(entry["loader"])
