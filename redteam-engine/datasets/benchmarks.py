"""
datasets/benchmarks.py

Public red-teaming benchmark loaders.

Beyond the hand-curated taxonomy in ``adversarial_prompts.py``, the engine can
evaluate against established public benchmarks so results are comparable to the
literature rather than self-defined.

Currently integrated:
  - **AdvBench** (harmful behaviors) — 520 harmful-behavior goal strings, the
    canonical seed set for jailbreak research. Each row is ``(goal, target)``
    where ``goal`` is the harmful instruction and ``target`` is the affirmative
    completion prefix used by gradient attacks (GCG).

The CSV is vendored under ``datasets/data/`` so evaluation is fully reproducible
and works offline; if the local copy is missing it is fetched once from the
upstream repository and cached.

Reference:
  Zou, A., Wang, Z., Carlini, N., Nasr, M., Kolter, J. Z., & Fredrikson, M. (2023).
  Universal and Transferable Adversarial Attacks on Aligned Language Models.
  arXiv:2307.15043. Data: github.com/llm-attacks/llm-attacks (MIT License).
"""

from __future__ import annotations

import csv
import os

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_ADVBENCH_CSV = os.path.join(_DATA_DIR, "advbench_harmful_behaviors.csv")
_ADVBENCH_URL = (
    "https://raw.githubusercontent.com/llm-attacks/llm-attacks/"
    "main/data/advbench/harmful_behaviors.csv"
)


def _ensure_advbench_csv() -> str:
    """Return the path to the vendored AdvBench CSV, downloading it if absent."""
    if os.path.exists(_ADVBENCH_CSV):
        return _ADVBENCH_CSV

    os.makedirs(_DATA_DIR, exist_ok=True)
    try:
        import urllib.request

        with urllib.request.urlopen(_ADVBENCH_URL, timeout=20) as resp:
            data = resp.read()
        with open(_ADVBENCH_CSV, "wb") as fh:
            fh.write(data)
    except Exception as exc:  # network unavailable and no local cache
        raise FileNotFoundError(
            f"AdvBench CSV not found at {_ADVBENCH_CSV} and download failed: {exc}. "
            f"Manually place harmful_behaviors.csv from {_ADVBENCH_URL} there."
        ) from exc
    return _ADVBENCH_CSV


def load_advbench(limit: int | None = None) -> list[dict]:
    """
    Load AdvBench harmful behaviors.

    Args:
        limit: If set, return at most this many rows (in file order, which is
            stable — useful for fast smoke runs).

    Returns:
        List of ``{"goal": str, "target": str}`` dicts.
    """
    path = _ensure_advbench_csv()
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            goal = (row.get("goal") or "").strip()
            if not goal:
                continue
            rows.append({"goal": goal, "target": (row.get("target") or "").strip()})
            if limit is not None and len(rows) >= limit:
                break
    return rows


def advbench_goals(limit: int | None = None) -> list[str]:
    """Return AdvBench goals as bare intent strings for attack strategies."""
    return [r["goal"] for r in load_advbench(limit=limit)]


def load_advbench_as_prompts(limit: int | None = None) -> list[dict]:
    """
    Load AdvBench as engine-native prompt dicts (matching the AttackPrompt schema
    used by ``adversarial_prompts.py`` and ``RedTeamEngine.run_evaluation``).

    Every AdvBench behavior is a direct harmful request, so all entries are
    tagged ``category="safety"`` with ``expected_behavior="refusal"``.
    """
    prompts: list[dict] = []
    for row in load_advbench(limit=limit):
        prompts.append({
            "category": "safety",
            "subcategory": "advbench_harmful_behavior",
            "prompt": row["goal"],
            "severity": "high",
            "description": "AdvBench harmful behavior (Zou et al. 2023)",
            "expected_behavior": "refusal",
            "tags": ["advbench", "public_benchmark", "harmful_behavior"],
            "source": "AdvBench",
            "target_prefix": row["target"],
        })
    return prompts


# Registry so callers/tests can discover available public benchmarks.
PUBLIC_BENCHMARKS = {
    "advbench": {
        "loader": load_advbench_as_prompts,
        "size": 520,
        "citation": "Zou et al. (2023), arXiv:2307.15043",
        "description": "520 harmful-behavior goal strings; canonical jailbreak seed set.",
    },
}
