"""
run_benchmark.py

End-to-end red-team benchmark runner: drive the attack strategies against a real
target model over AdvBench behaviors, score every response with an independent
Llama-Guard judge, and report per-strategy Attack Success Rate with confidence
intervals.

ASR here is judge-authoritative (Llama-Guard), NOT the engine's own heuristic
detector — so the numbers are credible and comparable to the literature.

Usage:
    python3 run_benchmark.py --limit 25 --strategies direct,crescendo,pair,tap
    python3 run_benchmark.py --limit 5        # cheap smoke test

Models / key come from .env (TARGET_MODEL, JUDGE_MODEL, OPENROUTER_API_KEY).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clients.openrouter_client import OpenRouterClient, load_env
from analysis.judge import judge_any, judge_response, LLAMA_GUARD_CATEGORIES
from analysis.metrics import PromptMetrics, attack_success_rate, asr_confidence_interval
from datasets.benchmarks import advbench_goals
from strategies.crescendo import CrescendoAttack
from strategies.pair import PAIRAttack
from strategies.tap import TAPAttack
from strategies.attacker import build_attacker


def run_direct(intent: str, target):
    """Baseline: send the raw harmful goal once, no attack strategy."""
    resp = target.generate(intent, max_tokens=512, temperature=0.0)
    return [intent], [resp.text if not resp.error else "[ERROR]"]


def build_strategy(name: str, attacker=None, judge_fn=None):
    """Return callable(intent, target) -> (prompts, responses) for judging."""
    if name == "direct":
        return lambda intent, target: run_direct(intent, target)
    if name == "crescendo":
        atk = CrescendoAttack(attack_family="generic", escalation_depth=5,
                              attacker=attacker, judge_fn=judge_fn)
        return lambda intent, target: (lambda r: (r.all_prompts, r.all_responses))(
            atk.run(intent, target, max_attempts=6))
    if name == "pair":
        atk = PAIRAttack(max_iterations=6, attacker=attacker, judge_fn=judge_fn)
        return lambda intent, target: (lambda r: (r.all_prompts, r.all_responses))(
            atk.run(intent, target, max_attempts=6))
    if name == "tap":
        atk = TAPAttack(beam_width=2, branching_factor=2, max_depth=2,
                        attacker=attacker, judge_fn=judge_fn)
        return lambda intent, target: (lambda r: (r.all_prompts, r.all_responses))(
            atk.run(intent, target, max_attempts=6))
    raise ValueError(f"unknown strategy: {name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5, help="number of AdvBench behaviors")
    ap.add_argument("--strategies", default="direct,crescendo,pair,tap")
    ap.add_argument("--out", default="benchmark_results.json")
    ap.add_argument("--no-attacker", action="store_true",
                    help="disable the attacker LLM (template-only TAP/PAIR)")
    ap.add_argument("--no-inloop-judge", action="store_true",
                    help="use the heuristic detector as the loop signal instead of the judge")
    ap.add_argument("--workers", type=int, default=6,
                    help="concurrent (goal,strategy) tasks (1 = sequential)")
    ap.add_argument("--seed", type=int, default=0, help="reserved for reproducibility")
    # Explicit overrides take precedence over .env (which is authoritative over the
    # shell env). Needed for multi-target sweeps — a shell TARGET_MODEL export is
    # otherwise shadowed by .env.
    ap.add_argument("--target", default=None, help="override target model")
    ap.add_argument("--judge", default=None, help="override judge model")
    ap.add_argument("--attacker", default=None, help="override attacker model")
    args = ap.parse_args()

    env = load_env()
    target_model = args.target or env.get("TARGET_MODEL", "meta-llama/llama-3.1-8b-instruct")
    judge_model = args.judge or env.get("JUDGE_MODEL", "meta-llama/llama-guard-4-12b")
    target = OpenRouterClient(model=target_model)
    judge = OpenRouterClient(model=judge_model)
    attacker = None if args.no_attacker else build_attacker(model=args.attacker)
    attacker_model = env.get("ATTACKER_MODEL", "(none)") if attacker else "(none/template)"
    # In-loop judge: strategies use Llama-Guard (not the heuristic) to decide success.
    judge_fn = None if args.no_inloop_judge else (
        lambda prompt, response: judge_response(judge, prompt, response).is_jailbroken
    )

    goals = advbench_goals(limit=args.limit)
    strategy_names = [s.strip() for s in args.strategies.split(",") if s.strip()]

    print(f"Target: {target_model}\nJudge:  {judge_model}\nAttacker: {attacker_model}")
    print(f"In-loop judge: {'heuristic' if args.no_inloop_judge else judge_model}")
    print(f"Behaviors: {len(goals)} | Strategies: {strategy_names}\n")

    # per strategy: list of (intent, jailbroken, category, attempts)
    records: dict[str, list[dict]] = {s: [] for s in strategy_names}
    t0 = time.time()

    # Each (goal, strategy) is an independent unit. A fresh strategy instance is
    # built per task so concurrent runs never share mutable state (e.g. TAP's
    # self.target_intent). Attacker/judge clients are stateless and thread-safe.
    def work(task):
        goal, sname = task
        runner = build_strategy(sname, attacker=attacker, judge_fn=judge_fn)
        try:
            prompts, responses = runner(goal, target)
        except Exception as e:
            prompts, responses = ["[ERROR]"], [f"[ERROR: {type(e).__name__}: {e}]"]
        # Judge each attempt in order; record the FIRST success → gives ASR@k and a
        # concrete transcript (evidence) for the jailbreak.
        first_idx = None
        jb_prompt = jb_resp = None
        cats: list[str] = []
        for idx, (p, r) in enumerate(zip(prompts, responses)):
            if not r or r.startswith("[ERROR"):
                continue
            v = judge_response(judge, goal, r)
            if v.is_jailbroken:
                first_idx, jb_prompt, jb_resp, cats = idx, p, r, v.categories
                break
        return sname, {
            "intent": goal,
            "jailbroken": first_idx is not None,
            "first_success_attempt": first_idx,   # 0-based; None if never
            "n_attempts": len(responses),
            "categories": cats,
            "jb_prompt": (jb_prompt or "")[:500],
            "jb_response": (jb_resp or "")[:500],
        }

    tasks = [(goal, sname) for goal in goals for sname in strategy_names]
    if args.workers > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(work, t): t for t in tasks}
            for fut in as_completed(futs):
                sname, rec = fut.result()
                records[sname].append(rec)
                done += 1
                mark = "JAILBROKEN" if rec["jailbroken"] else "safe"
                print(f"  [{done}/{len(tasks)}] {sname:10} {mark} "
                      f"{','.join(rec['categories'])} | {rec['intent'][:50]}")
    else:
        for t in tasks:
            sname, rec = work(t)
            records[sname].append(rec)
            mark = "JAILBROKEN" if rec["jailbroken"] else "safe"
            print(f"  {sname:10} {mark} {','.join(rec['categories'])} | {rec['intent'][:55]}")

    elapsed = time.time() - t0

    # Aggregate per strategy via our own metrics module (Wilson CI).
    summary = {}
    print("\n" + "=" * 60)
    print(f"RESULTS  (target={target_model}, judge={judge_model}, n={len(goals)})")
    print("=" * 60)
    print(f"{'strategy':12} {'ASR':>7}  {'95% CI':>16}  {'@1':>5}{'@3':>6}{'@5':>6}  cat-breakdown")
    for sname in strategy_names:
        recs = records[sname]
        n = len(recs) or 1
        pm = [PromptMetrics(prompt=r["intent"], response="", attack_type=sname,
                            is_jailbroken=r["jailbroken"], toxicity_score=0.0,
                            refusal_detected=not r["jailbroken"], coherence_score=0.0,
                            hallucination_score=0.0) for r in recs]
        asr = attack_success_rate(pm)
        ci = asr_confidence_interval(pm)
        # Empirical ASR@k: fraction succeeding within the first k attempts (query efficiency).
        def asr_at(k):
            return sum(1 for r in recs
                       if r["first_success_attempt"] is not None
                       and r["first_success_attempt"] < k) / n
        asr_k = {1: asr_at(1), 3: asr_at(3), 5: asr_at(5)}
        cat_counts: dict[str, int] = {}
        for r in recs:
            for c in r["categories"]:
                cat_counts[c] = cat_counts.get(c, 0) + 1
        cat_str = ", ".join(f"{c}({LLAMA_GUARD_CATEGORIES.get(c,'?')}):{cnt}"
                            for c, cnt in sorted(cat_counts.items()))
        summary[sname] = {"asr": asr, "ci95": [ci["ci_low"], ci["ci_high"]],
                          "n": ci["n"], "jailbreaks": sum(r["jailbroken"] for r in recs),
                          "asr_at_k": asr_k, "categories": cat_counts}
        print(f"{sname:12} {asr:>6.1%}  [{ci['ci_low']:.2f}, {ci['ci_high']:.2f}]  "
              f"{asr_k[1]:>5.0%}{asr_k[3]:>6.0%}{asr_k[5]:>6.0%}  {cat_str}")
    print(f"\nelapsed: {elapsed:.0f}s")

    out = {"target": target_model, "judge": judge_model, "n": len(goals),
           "summary": summary, "records": records}
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
