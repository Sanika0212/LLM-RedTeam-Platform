"""
Tests for strategies/attacker.py and attacker integration into the strategies.

Network-free: a FakeClient stands in for the OpenRouter attacker model so we can
verify the attacker is used when present and that strategies fall back to
templates when it is absent or errors.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import dataclass

from strategies.attacker import AttackerLLM
from strategies.tap import TAPAttack
from strategies.pair import PAIRAttack, FailureMode
from strategies.crescendo import CrescendoAttack


@dataclass
class FakeResp:
    text: str
    error: str | None = None


class FakeAttackerClient:
    """Returns a canned adversarial prompt, tagged with the call index."""
    def __init__(self):
        self.calls = 0
        self.model = "fake/attacker"

    def generate(self, prompt, system_prompt="", max_tokens=300, temperature=1.0):
        self.calls += 1
        return FakeResp(text=f"ADVERSARIAL_PROMPT_{self.calls} for context")


class ErroringClient:
    model = "fake/erroring"
    def generate(self, prompt, system_prompt="", max_tokens=300, temperature=1.0):
        return FakeResp(text="", error="boom")


class TargetStub:
    """Minimal target: always refuses, supports generate + generate_chat."""
    def generate(self, prompt, max_tokens=512, temperature=0.7):
        return FakeResp(text="I cannot help with that.")
    def generate_chat(self, messages, max_tokens=512, temperature=0.7):
        return FakeResp(text="I cannot help with that.")


class TestAttackerLLM:
    def test_propose_returns_n(self):
        a = AttackerLLM(FakeAttackerClient())
        out = a.propose("teach lockpicking", 3)
        assert len(out) == 3
        assert all("ADVERSARIAL_PROMPT_" in p for p in out)

    def test_refine_returns_string(self):
        a = AttackerLLM(FakeAttackerClient())
        out = a.refine("teach lockpicking", "prev prompt", "I refuse.", failure_mode="explicit_refusal")
        assert isinstance(out, str) and out

    def test_errors_yield_none_or_empty(self):
        a = AttackerLLM(ErroringClient())
        assert a.refine("x", "y", "z") is None
        assert a.propose("x", 3) == []


class TestTAPAttackerIntegration:
    def test_mutate_uses_attacker_when_present(self):
        tap = TAPAttack(attacker=AttackerLLM(FakeAttackerClient()))
        tap.target_intent = "teach lockpicking"
        muts = tap._mutate("parent prompt", 2, last_response="I refuse.")
        assert len(muts) == 2
        assert all("ADVERSARIAL_PROMPT_" in m for m in muts)

    def test_mutate_falls_back_to_templates_when_attacker_errors(self):
        tap = TAPAttack(attacker=AttackerLLM(ErroringClient()))
        tap.target_intent = "teach lockpicking"
        muts = tap._mutate("parent prompt", 2)
        # template fallback still yields prompts containing the parent
        assert len(muts) == 2
        assert all("parent prompt" in m for m in muts)

    def test_no_attacker_uses_templates(self):
        tap = TAPAttack()
        tap.target_intent = "x"
        muts = tap._mutate("parent prompt", 2)
        assert all("parent prompt" in m for m in muts)


class TestPAIRAttackerIntegration:
    def test_refine_uses_attacker(self):
        pair = PAIRAttack(attacker=AttackerLLM(FakeAttackerClient()))
        out = pair._refine("cur prompt", "intent", FailureMode.EXPLICIT_REFUSAL, last_response="no")
        assert "ADVERSARIAL_PROMPT_" in out

    def test_refine_falls_back_without_attacker(self):
        pair = PAIRAttack()
        out = pair._refine("cur prompt", "INTENT_TOKEN", FailureMode.EXPLICIT_REFUSAL)
        assert "INTENT_TOKEN" in out  # template path embeds the intent


class TestCrescendoAttackerIntegration:
    def test_attacker_drives_turns(self):
        cres = CrescendoAttack(escalation_depth=3, attacker=AttackerLLM(FakeAttackerClient()))
        res = cres.run("teach lockpicking", TargetStub(), max_attempts=6)
        # every user turn should be an attacker-generated prompt
        assert res.all_prompts
        assert all("ADVERSARIAL_PROMPT_" in p for p in res.all_prompts)

    def test_no_attacker_uses_template_sequence(self):
        cres = CrescendoAttack(escalation_depth=3)
        res = cres.run("data exfiltration", TargetStub(), max_attempts=6)
        # template path: generic escalation steps mention the topic
        assert res.all_prompts
        assert any("data exfiltration" in p for p in res.all_prompts)


class TestInLoopJudge:
    def test_judge_fn_overrides_heuristic_success(self):
        # TargetStub always refuses (heuristic would say not-jailbroken), but an
        # injected judge_fn that returns True must make the strategy register
        # success on the first turn.
        cres = CrescendoAttack(escalation_depth=5, judge_fn=lambda p, r: True)
        res = cres.run("x", TargetStub(), max_attempts=6)
        assert res.success is True
        assert len(res.all_prompts) == 1  # stopped immediately on judge success

    def test_judge_fn_false_keeps_going(self):
        # judge_fn always False → never succeeds, runs the full depth.
        cres = CrescendoAttack(escalation_depth=3, judge_fn=lambda p, r: False)
        res = cres.run("x", TargetStub(), max_attempts=6)
        assert res.success is False

    def test_judge_fn_exception_falls_back_to_heuristic(self):
        # A throwing judge_fn must not crash the run (falls back to heuristic).
        def boom(p, r):
            raise RuntimeError("judge down")
        tap = TAPAttack(beam_width=1, branching_factor=1, max_depth=1, judge_fn=boom)
        res = tap.run("x", TargetStub(), max_attempts=2)
        assert res is not None  # completed without raising
