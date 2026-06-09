"""
Tests for generators.py — adversarial prompt mutation / encoding / expansion.

Previously uncovered by the suite; added alongside the base64 encoding operator.
"""
import sys
import os
import base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from generators import (
    _apply_encoding,
    generate_encoding_variants,
    generate_register_variants,
    expand_prompts,
    expand_for_benchmark,
)

SEED = {"prompt": "explain the secret method", "category": "jailbreak", "subcategory": "test"}


class TestEncodingOperators:
    def test_base64_round_trips_payload(self):
        out = _apply_encoding("attack payload here", "base64")
        # The original text must NOT appear in cleartext...
        assert "attack payload here" not in out
        # ...but must be recoverable from the embedded base64 blob.
        blob = out.split()[-1]
        assert base64.b64decode(blob).decode() == "attack payload here"

    def test_base64_has_decode_instruction(self):
        out = _apply_encoding("x", "base64")
        assert "base64" in out.lower() and "decode" in out.lower()

    def test_leetspeak_substitutes(self):
        assert _apply_encoding("elite", "leetspeak") == "3l173"

    def test_reversed(self):
        assert _apply_encoding("abc", "reversed") == "cba"

    def test_unknown_encoding_is_identity(self):
        assert _apply_encoding("abc", "nonexistent") == "abc"


class TestEncodingVariants:
    def test_base64_in_defaults(self):
        variants = generate_encoding_variants(SEED)
        subs = [v["subcategory"] for v in variants]
        assert any(s.endswith("_base64") for s in subs)

    def test_variants_drop_id_and_keep_category(self):
        seed = {**SEED, "id": 99}
        for v in generate_encoding_variants(seed):
            assert "id" not in v
            assert v["category"] == "jailbreak"


class TestRegisterVariants:
    def test_three_registers(self):
        variants = generate_register_variants(SEED)
        assert len(variants) == 3
        assert all(SEED["prompt"] in v["prompt"] for v in variants)


class TestExpand:
    def test_expand_keeps_originals(self):
        out = expand_prompts([SEED], multiplier=2)
        assert SEED in out
        assert len(out) >= 3  # original + 2 variants

    def test_expand_variants_embed_original(self):
        out = expand_prompts([SEED], multiplier=2)
        variants = [p for p in out if p is not SEED]
        assert all(SEED["prompt"] in v["prompt"] for v in variants)

    def test_expand_for_benchmark_includes_base64(self):
        out = expand_for_benchmark([SEED], mutation_multiplier=2)
        assert any(v["subcategory"].endswith("_base64") for v in out)
