"""Tests for EvalService with mock LLM client."""

import os
import sys
from dataclasses import dataclass
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "redteam-engine"))

import pytest
from core import RedTeamEngine, PromptResult


@dataclass
class MockLLMResponse:
    text: str
    model: str = "mock-model"
    provider: str = "mock"
    usage: dict = None
    raw: dict = None
    error: str = None

    def __post_init__(self):
        if self.usage is None:
            self.usage = {}
        if self.raw is None:
            self.raw = {}


class MockLLMClient:
    """Deterministic mock LLM client for testing."""

    def __init__(self, responses=None):
        self._responses = responses or []
        self._call_count = 0

    def generate(self, prompt, max_tokens=1024, temperature=0.0, system_prompt=None):
        if self._responses:
            resp = self._responses[self._call_count % len(self._responses)]
            self._call_count += 1
            return MockLLMResponse(text=resp)
        # Default: refuse
        return MockLLMResponse(
            text="I'm sorry, but I can't help with that request. As an AI, I must decline."
        )

    def is_available(self):
        return True

    @property
    def provider_name(self):
        return "mock"


def test_engine_evaluate_prompt_refusal():
    client = MockLLMClient()
    engine = RedTeamEngine(client)
    result = engine.evaluate_prompt("Do something bad", "jailbreak", "refusal")
    assert isinstance(result, PromptResult)
    assert result.is_jailbroken is False
    assert result.refusal_detected is True


def test_engine_evaluate_prompt_jailbroken():
    client = MockLLMClient(responses=[
        "Sure, here's how to do it. Step 1: First, you need to gather materials."
    ])
    engine = RedTeamEngine(client)
    result = engine.evaluate_prompt("Do something bad", "jailbreak", "refusal")
    assert result.is_jailbroken is True


def test_engine_evaluate_prompt_error():
    client = MockLLMClient()
    client.generate = lambda **kwargs: MockLLMResponse(text="", error="API error")
    engine = RedTeamEngine(client)
    result = engine.evaluate_prompt("test", "jailbreak")
    assert "[ERROR" in result.response
    assert result.is_jailbroken is False


def test_engine_run_evaluation():
    client = MockLLMClient(responses=[
        "I'm sorry, but I can't assist with that.",
        "Sure, here's how to do it. Step 1: gather materials.",
        "I cannot help with harmful requests. As an AI, I must decline.",
    ])
    engine = RedTeamEngine(client)
    prompts = [
        {"prompt": "Prompt 1", "category": "jailbreak", "expected_behavior": "refusal"},
        {"prompt": "Prompt 2", "category": "jailbreak", "expected_behavior": "refusal"},
        {"prompt": "Prompt 3", "category": "safety", "expected_behavior": "refusal"},
    ]
    progress_calls = []
    results = engine.run_evaluation(prompts, on_progress=lambda c, t: progress_calls.append((c, t)))
    assert len(results) == 3
    assert len(progress_calls) == 3
    assert progress_calls[-1] == (3, 3)


def test_compute_aggregate_scores():
    results = [
        PromptResult("p1", "r1", "jailbreak", True, 0.5, 0.8, False, 0.1),
        PromptResult("p2", "r2", "jailbreak", False, 0.0, 0.9, True, 0.0),
        PromptResult("p3", "r3", "safety", False, 0.1, 0.7, True, 0.3),
        PromptResult("p4", "r4", "safety", True, 0.8, 0.6, False, 0.2),
    ]
    scores = RedTeamEngine.compute_aggregate_scores(results)
    assert scores["jailbreak_rate"] == 0.5  # 2/4
    assert scores["safety_score"] == 0.5  # 1 - 0.5
    assert scores["robustness_score"] == 0.5  # 2/4 refusals
    assert scores["hallucination_rate"] == 0.15  # (0.1+0+0.3+0.2)/4


def test_compute_aggregate_scores_empty():
    scores = RedTeamEngine.compute_aggregate_scores([])
    assert scores["safety_score"] == 0
    assert scores["jailbreak_rate"] == 0
