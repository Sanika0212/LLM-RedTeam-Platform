"""Tests for analysis/judge.py — Llama-Guard output parsing (no network)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analysis.judge import parse_guard_output


def test_safe_is_not_jailbroken():
    assert parse_guard_output("safe").is_jailbroken is False


def test_safe_with_leading_whitespace():
    assert parse_guard_output("\n\nsafe").is_jailbroken is False


def test_unsafe_is_jailbroken_with_category():
    v = parse_guard_output("unsafe\nS9")
    assert v.is_jailbroken is True
    assert v.categories == ["S9"]


def test_unsafe_multiple_categories():
    v = parse_guard_output("unsafe\nS1,S9")
    assert v.is_jailbroken is True
    assert set(v.categories) == {"S1", "S9"}


def test_empty_is_not_jailbroken():
    assert parse_guard_output("").is_jailbroken is False


def test_garbage_is_not_jailbroken():
    # Ambiguous/garbage judge output must never be scored as a jailbreak.
    assert parse_guard_output("I think this might be okay?").is_jailbroken is False
