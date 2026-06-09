# Re-Audit Status Report — LLM Red-Team & Evaluation Platform
### Post-"Fix 11 audit findings" commit (`9e9dfa2`)

## 1. Verdict

Of the 21 originally-modified findings, **11 are genuinely fixed**, **2 are partial** (IN5, TE5), and **8 are not fixed** (DE6, IN4, DE8, DE9, BA3, FR4, DE11, ME3) — including two where the patch is a no-op or wrong-API copy (BA3's `require`/`verify_exp` keys have no effect in python-jose; the fix only superficially "looks" applied). Critically, **the commit introduced 6 new bugs**, one of them **critical** (a blanket 401→`window.location.reload()` in `request()` silently breaks the login flow so wrong-password errors never surface) and three **high** (errored prompts re-persisted as clean rows re-polluting downstream analytics; all-errored runs marked `completed`; a config `ValueError` raised outside the try/except leaves evals stuck `pending`). Net research-trustworthiness moved **sideways-to-slightly-negative**: the headline error-exclusion fix (EV1/EN1/IN5) is undermined at the persistence layer, so stored aggregates and row-recomputed analytics now actively disagree, and the multi-turn drift pipeline (DE6/DE9/DE11) remains scientifically invalid. Security posture is **roughly unchanged**: FR2's reactive auto-logout is a genuine win, but BA3 (exp enforcement) is a non-fix and FR4 (token in localStorage) is untouched, while the new login-flow regression is a usability/availability defect, not a hardening one.

## 2. Status Table (21 modified findings)

| ID | Sev | Status | Note |
|----|-----|--------|------|
| DE1 | critical | ✅ fixed | Word-boundary regex resolves over-flagging; recall caveat is separate, pre-acknowledged |
| DE2 | critical | ✅ fixed | Four bare harm words removed; defect class eliminated (boundary matching not added but not needed for scope) |
| EV1 | critical | ✅ fixed | Errors tagged `is_error` and excluded from all denominators |
| IN1 | critical | ✅ fixed | HF/custom no longer aliased to OpenAI; honors `api_endpoint` |
| DE6 | high | ❌ not fixed | Drift still computed over fake "conversations" grouped by attack_type/row-id; no conversation_id/turn cols |
| DE7 | high | ✅ fixed | Yes-ladder now uses strict monotonic comparisons |
| EN1 | high | ✅ fixed | Error exclusion applied to all rate denominators |
| IN4 | high | ❌ not fixed | Still no per-request `timeout`/`max_retries`; SDK ~600s default still blocks worker slots |
| IN5 | high | 🟡 partial | Metric bias gone, but status still `completed` on errors and `errored_prompts` never persisted |
| FR1 | high | ✅ fixed | CSV export uses authenticated POST + blob download |
| DE8 | medium | ❌ not fixed | `is_jailbroken` and `refusal_detected` still unreconciled; no mutual-exclusivity assert |
| DE9 | medium | ❌ not fixed | SentenceTransformer still re-instantiated per pair; no module cache/batch encode |
| ST2 | medium | ✅ fixed | TOO_EXPLICIT branch now exists before EXPLICIT_REFUSAL (but over-fires — see regressions) |
| BA3 | medium | ❌ not fixed | `options={"require":[...]}`/`verify_exp` are no-ops in python-jose; exp still not required |
| FR2 | medium | ✅ fixed | 401 → clearToken + reload in both request() and CSV paths (but see new login regression) |
| FR3 | medium | ✅ fixed | Insufficient-data `{error}` object routed to error card |
| FR4 | medium | ❌ not fixed | JWT still in JS-readable localStorage; no httpOnly cookie, no CSP; 120-min expiry |
| ME2 | low | ✅ fixed | Empty-input now returns 1.0, consistent with `compute_all_metrics` |
| DE11 | low | ❌ not fixed | x10 scaling, static density (not trend), and 0.001 threshold all unchanged |
| TE5 | low | 🟡 partial | Missing empty-list/k=0 tests; aliased `*3` fixture remains; k-overshoot uncovered |
| ME3 | info | ❌ not fixed | `asr_at_k` still has no `k<=0` guard (ZeroDivisionError / meaningless value) |

## 3. Fixes That Are Incomplete or Wrong

**IN5 (high → now low) — partial.** Metric bias is resolved, but two pieces remain: (1) `eval_service.py:114` sets `status="completed"` unconditionally even when `aggregates["errored_prompts"] > 0`; (2) the new `errored_prompts`/`valid_prompts` counts are computed but never persisted (no column on the `Evaluation` model). An all-errored run still shows `safety_score=0` and `completed` silently.
*Fix:* add `errored_prompts`(+`valid_prompts`) Integer column + migration, persist `aggregates["errored_prompts"]`, and set `status="completed_with_errors"` (or `failed`) when `errored_prompts > 0`.

**TE5 (low) — partial.** Two of four recommended tests missing, one half-applied: no `asr_at_k([], k)` test; no `asr_at_k(results, 0)` test (leaves ME3 contract uncovered); aliased fixture `[make_result(is_jailbroken=False)] * 3` still at line 94 (false-green risk); `group[:k]` overshoot (k > group length) never asserted.
*Fix:* add `assert asr_at_k([], 5) == 0.0` and `assert asr_at_k([make_result(is_jailbroken=True)], 0) == 0.0`; rewrite line 94 to `[[make_result(is_jailbroken=False) for _ in range(3)] for _ in range(5)]`; add an empirical case with `k=5` beyond group length.

**DE6 (high) — not fixed.** Endpoint still fabricates conversations from independent single-shot results grouped by `attack_type` ordered by row id; no `conversation_id`/`turn_index` columns; detector has no provenance guard. (It also reads non-existent `r.prompt_text`/`r.response_text` — columns are `prompt`/`response` — so fabricated turns are empty strings.)
*Fix:* add `conversation_id` + `turn_index` to `EvaluationResult` (populated from real Crescendo/PAIR/TAP transcripts), group/order by `(conversation_id, turn_index)`, and make `detect_semantic_drift` validate provenance and reject fabricated groupings.

**IN4 (high) — not fixed.** Neither SDK client sets per-request `timeout`/`max_retries`; SDK ~600s default still applies, so hung provider calls block all 4 worker slots (compounds IN3).
*Fix:* `OpenAI(..., timeout=60, max_retries=2)` and `anthropic.Anthropic(..., timeout=60, max_retries=2)` (or per-request `timeout=`), sourced from a shared constant well under the Celery task limit.

**DE8 (medium) — not fixed.** `is_jailbroken` and `refusal_detected` remain two unreconciled detector outputs; one row can feed both the jailbreak and refusal numerators.
*Fix:* reconcile in `evaluate_prompt` before building `PromptResult`, e.g. `refusal_detected = refusal_result["refusal_detected"] and not is_jailbroken`, plus `assert not (is_jailbroken and refusal_detected)`.

**DE9 (medium) — not fixed.** `_semantic_distance` re-instantiates `SentenceTransformer` per call; timeouts silently fall back to Jaccard.
*Fix:* module-level `_get_st_model()` cache; load once and batch-encode all responses in a single `model.encode([...])`.

**BA3 (medium) — not fixed (wrong API).** The patch copied PyJWT's `options={"require": [...]}` / `verify_exp` into python-jose, where those keys have no effect — `exp` is still not *required*, so exp-less tokens never expire.
*Fix:* use python-jose's real API: `options={"require_exp": True}` (auto-forces `verify_exp`), optionally `"require_sub": True`; or migrate to PyJWT. Add a regression test minting an exp-less token and asserting `decode_token(...) is None`.

**FR4 (medium) — not fixed.** JWT still in JS-readable localStorage; no httpOnly cookie, no CSP; default 120-min expiry. (The new `exp` claim is the BA3 attempt, not an FR4 mitigation; FR2 auto-logout doesn't help an already-exfiltrated token.)
*Fix:* backend sets JWT in `httpOnly; Secure; SameSite=Strict|Lax` cookie on `/auth/login` + `/auth/register` (drop from JSON body), read via `credentials: 'include'`, add a restrictive CSP. If localStorage must stay, add CSP + reduce `ACCESS_TOKEN_EXPIRE_MINUTES` (e.g. 15) with refresh.

**DE11 (low) — not fixed.** Patch only touched DE7. The x10 scaling (`info_disclosure_rate * 10 * 0.10`), the static density `info_disclosure_rate` (not a late-minus-early trend), and the 0.001 evidence threshold are all byte-for-byte unchanged.
*Fix:* replace with a cross-turn delta (`disclosure_trend = max(late_density - early_density, 0)`), clamp its drift contribution (`min(disclosure_trend*10, 0.10)*0.10`), and raise the threshold above per-word keyword noise (~0.01 AND positive trend).

**ME3 (info) — not fixed.** `asr_at_k` still does `1.0 - (1.0 - asr) ** k` with no guard: `k<0` (asr==1.0) → ZeroDivisionError; `k==0` → meaningless 0.0.
*Fix:* `if k <= 0: raise ValueError(...)` at the top, and document the positive-k contract.

## 4. New Regressions Introduced by the Fix Commit

| # | Title | File:line | Sev | Fix |
|---|-------|-----------|-----|-----|
| R1 | 401-reload in `request()` breaks login flow — wrong-password 401 silently reloads, error never surfaced | `frontend/src/services/api.ts:34-39, 51-55` | ⛔ critical | Guard the 401 handler for auth endpoints: `if (res.status === 401 && !path.startsWith('/auth/'))` (or only when `getToken()` present) and still `throw` so `Login.tsx` shows "Invalid email or password" |
| R2 | Errored prompts persisted as normal `EvaluationResult` rows, re-polluting downstream analytics the fix protected | `backend/services/eval_service.py:93-106` | high | Skip persisting errored results (`if r.is_error: continue`) OR add `is_error` column + filter `is_error==0` in `analytics.py` category_heatmap (~291), vulnerability-profile (~86), and evaluation-report |
| R3 | Evaluation marked `completed` even when every prompt errored (zero-dict scores look like a real maximally-unsafe result) | `backend/services/eval_service.py:108-116` | high | Branch on new keys: `if aggregates['valid_prompts'] == 0: evaluation.status = 'failed'`; persist `errored_prompts`/`valid_prompts` |
| R4 | Config `ValueError` raised OUTSIDE eval_service try/except → misconfigured custom model leaves eval stuck `pending` (sync path) | `backend/services/eval_service.py:61-91` | high | Move `get_llm_client()` inside a try that marks the eval `failed` on error (or after status bookkeeping, wrapped) so the record reflects the misconfiguration on any call path |
| R5 | 401-reload not guarded by "was authenticated" → reload loop if any token-less request returns 401 (duplicated in CSV path) | `frontend/src/services/api.ts:34-39, 100` | high | Guard with `if (res.status === 401 && getToken())`; add a module-level `reloading` flag; factor the 401 handling into one shared helper |
| R6 | Celery treats non-transient config `ValueError` as retryable — wastes 2 retries (~60s) + log flood per misconfigured model | `workers/tasks/evaluation_task.py:19-37` | medium | Catch `ValueError` separately, mark failed, do NOT retry (`return`/`Ignore()`); reserve `self.retry` for transient network/provider errors |
| R7 | `model.safety_score`/`robustness_score` overwritten with misleading zeros on an all-errored run (clobbers good prior scores, corrupts leaderboard) | `backend/services/eval_service.py:118-121` | medium | Guard model-score update + `total_evaluations++` on `aggregates['valid_prompts'] > 0` |
| R8 | Average-safety dashboard dilutes fleet safety with all-errored zero rows | `backend/api/routes/evaluations.py:179-188` | low | Once R3 marks errored runs `failed`, filter aggregation to `status=='completed'` with `valid_prompts>0` |
| R9 | `validate_model_connection` throws uncaught `ValueError` instead of `{reachable: False}` dict (latent — no route caller today) | `backend/services/model_service.py:8-21` | low | Wrap `get_llm_client` in `try/except ValueError` → return `{'reachable': False, 'error': str(e)}` |

*Verified NOT regressions (info-level checks that passed):* `super().__init__` signature is correct (no crash on OpenAI evals); `api_endpoint` is threaded end-to-end from the model record; `exportEvaluationCsv` caller migrated correctly to `Promise<void>` (no stale URL-string consumers); toxicity `\b` regex handles multi-word keywords safely (latent, none present today) and its word-count denominator is consistent with case-insensitive matching.

## 5. Still Open (Untouched by This Commit)

**37 confirmed findings in files this commit did not touch remain OPEN by definition — not addressed.** Breakdown:

- **2 critical:**
  - **IN2** — Celery retry duplicates result rows (re-running a task re-persists `EvaluationResult` rows; compounds the R2/R3 persistence problems above).
  - **IN1-ci** — CI runs only 4 of 9 engine test files, so most detector/strategy regressions ship unverified (and would not have caught the partial/not-fixed items above).
- **10 high, 13 medium, 12 low** — all unchanged.

These 35 non-critical + 2 critical findings live outside the modified files and received no attention in `9e9dfa2`.

## 6. Recommended Next Commit (ordered punch-list)

**Tier 0 — Stop active harm / data corruption (do first):**
1. **R1 (critical):** Guard the 401-reload so it never fires for `/auth/*` and re-throws — restore the login error path.
2. **R2 (high):** Stop persisting errored prompts as clean rows (skip or add `is_error` column + filter all row-recomputing analytics) — finishes the EV1/EN1/IN5 fix at the persistence layer.
3. **R3 + IN5 (high):** Mark all-errored runs `failed`/`completed_with_errors`; persist `errored_prompts`/`valid_prompts`.
4. **R4 (high):** Wrap `get_llm_client()` so config errors mark the eval `failed` on both sync and Celery paths (don't leave `pending`).
5. **R5 (high):** Add `getToken()` guard + reload-once flag to the shared 401 handler (request() + CSV).

**Tier 1 — Open criticals (untouched findings):**
6. **IN2 (critical):** Make result persistence idempotent so Celery retries don't duplicate `EvaluationResult` rows.
7. **IN1-ci (critical):** Wire all 9 engine test files into CI so the remaining fixes are actually verified.

**Tier 2 — Remaining new-regression cleanup:**
8. **R7 (medium):** Guard `model.safety_score`/`total_evaluations` update on `valid_prompts > 0`.
9. **R6 (medium):** Don't retry config `ValueError` in the Celery task.
10. **R8 (low):** Exclude zero-valid runs from the fleet-average dashboard.
11. **R9 (low):** Restore `validate_model_connection` dict contract.

**Tier 3 — Finish the incomplete/not-fixed originals:**
12. **IN4 (high):** Add SDK `timeout`/`max_retries`.
13. **DE6 (high):** Real `conversation_id`/`turn_index` columns + provenance guard (also fixes the `prompt_text`/`response_text` attribute bug).
14. **BA3 (medium):** Correct python-jose `options={"require_exp": True}` + regression test.
15. **DE8 (medium):** Reconcile `is_jailbroken`/`refusal_detected` + mutual-exclusivity assert.
16. **DE9 (medium):** Cache + batch-encode the SentenceTransformer model.
17. **FR4 (medium):** Move JWT to an httpOnly cookie + add CSP (or shorten expiry).
18. **DE11 (low):** Replace x10 static-density disclosure term with a clamped cross-turn trend + higher threshold.
19. **TE5 (low):** Add the missing empty-list/`k=0`/overshoot tests; de-alias the `*3` fixture.
20. **ME3 (info):** Add the `k <= 0` guard to `asr_at_k`.
---

## Addendum — two PAIR regressions (surfaced by the regression pass, not numbered above)

The ST2 fix (`pair.py`) resolves the literal finding ("`TOO_EXPLICIT` never produced") but over-corrects, creating two new defects:

| # | Title | File:line | Sev | Fix |
|---|-------|-----------|-----|-----|
| R10 | New `TOO_EXPLICIT` branch (`<50 words` + no moralizing) fires BEFORE `EXPLICIT_REFUSAL` and steals nearly all real short refusals, **inverting `mode_distribution`** | `redteam-engine/strategies/pair.py:108-120` | high | Require a positive TOO_EXPLICIT signal (e.g. response restates/echoes the harmful request verbatim) rather than "short refusal w/o lecture"; keep EXPLICIT_REFUSAL as the default for plain refusals |
| R11 | Mislabeling routes the dominant failure case to the wrong refinement operator, degrading PAIR's attack search | `redteam-engine/strategies/pair.py:199-212, 441-448` | medium | Follows from R10 — once TOO_EXPLICIT only fires on true echo-then-refuse, operator routing self-corrects; add a unit test asserting a plain "I can't help with that." → `EXPLICIT_REFUSAL` |

Net: **ST2 is "fixed in letter, regressed in spirit"** — the mode now exists but is over-assigned, so the PAIR failure-mode histogram (a paper figure) is now wrong in the opposite direction.
