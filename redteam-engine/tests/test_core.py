"""Tests for RedTeamEngine core orchestrator."""

import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import RedTeamEngine, PromptResult


@dataclass
class MockLLMResponse:
    text: str
    model: str = "mock"
    provider: str = "mock"
    usage: dict = None
    raw: dict = None
    error: str = None

    def __post_init__(self):
        if self.usage is None:
            self.usage = {}
        if self.raw is None:
            self.raw = {}


class MockClient:
    def __init__(self, responses):
        self._responses = responses
        self._idx = 0

    def generate(self, prompt, max_tokens=1024, temperature=0.0, system_prompt=None):
        resp = self._responses[self._idx % len(self._responses)]
        self._idx += 1
        return MockLLMResponse(text=resp)


def test_evaluate_prompt_returns_prompt_result():
    client = MockClient(["I'm sorry, but I can't help with that."])
    engine = RedTeamEngine(client)
    result = engine.evaluate_prompt("test prompt", "jailbreak")
    assert isinstance(result, PromptResult)
    assert result.prompt == "test prompt"
    assert result.attack_type == "jailbreak"


def test_evaluate_prompt_with_error():
    client = MockClient([""])
    client.generate = lambda **kwargs: MockLLMResponse(text="", error="timeout")
    engine = RedTeamEngine(client)
    result = engine.evaluate_prompt("test", "jailbreak")
    assert "ERROR" in result.response
    assert result.extra_data.get("error") == "timeout"


def test_run_evaluation_processes_all():
    client = MockClient([
        "I cannot assist with that.",
        "Sure, here's how to do it. Step 1: start here.",
    ])
    engine = RedTeamEngine(client)
    prompts = [
        {"prompt": "P1", "category": "jailbreak", "expected_behavior": "refusal"},
        {"prompt": "P2", "category": "jailbreak", "expected_behavior": "refusal"},
    ]
    results = engine.run_evaluation(prompts)
    assert len(results) == 2
    assert results[0].refusal_detected is True
    assert results[1].is_jailbroken is True


def test_run_evaluation_progress_callback():
    client = MockClient(["I'm sorry, I can't."])
    engine = RedTeamEngine(client)
    prompts = [{"prompt": f"P{i}", "category": "test"} for i in range(5)]
    progress = []
    engine.run_evaluation(prompts, on_progress=lambda c, t: progress.append((c, t)))
    assert len(progress) == 5
    assert progress[0] == (1, 5)
    assert progress[-1] == (5, 5)


def test_score_coherence_empty():
    assert RedTeamEngine._score_coherence("") == 0.0


def test_score_coherence_no_sentences():
    # "hello" splits to one sentence with 1 word — avg_len < 5, returns 0.5
    assert RedTeamEngine._score_coherence("hello") == 0.5


def test_score_coherence_normal():
    text = "This is a normal sentence with enough words to score well. It has reasonable length for analysis. The content is coherent and well structured overall."
    score = RedTeamEngine._score_coherence(text)
    assert 0.7 <= score <= 1.0


def test_aggregate_scores_all_jailbroken():
    results = [
        PromptResult("p", "r", "jailbreak", True, 0.0, 0.8, False, 0.0),
        PromptResult("p", "r", "jailbreak", True, 0.0, 0.8, False, 0.0),
    ]
    scores = RedTeamEngine.compute_aggregate_scores(results)
    assert scores["jailbreak_rate"] == 1.0
    assert scores["safety_score"] == 0.0


def test_aggregate_scores_none_jailbroken():
    results = [
        PromptResult("p", "r", "jailbreak", False, 0.0, 0.8, True, 0.0),
        PromptResult("p", "r", "jailbreak", False, 0.0, 0.8, True, 0.0),
    ]
    scores = RedTeamEngine.compute_aggregate_scores(results)
    assert scores["jailbreak_rate"] == 0.0
    assert scores["safety_score"] == 1.0
    assert scores["robustness_score"] == 1.0
