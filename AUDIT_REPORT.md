# LLM Red-Team & Evaluation Platform — Security & Research-Validity Audit

**Auditor:** Lead Auditor
**Scope:** redteam-engine, backend, workers, frontend, infrastructure/CI
**Method:** Independent findings, each re-verified against the real code by an adversarial skeptic. 57 findings survived verification.

---

## 1. Executive Summary

The platform is **functional but its research outputs cannot currently be trusted**, and its multi-tenant data is **not protected**. The most serious theme is research-validity corruption that begins at the detector layer and propagates all the way to the paper's headline numbers: the default-install toxicity path uses naive substring matching (`die` ∈ `studied`), refusal detection fires on generic harm words present in *compliant* jailbreaks, the "hallucination" detector actually scores citation density (well-sourced true answers score *higher*), and the multi-turn "semantic drift" detector is fed unrelated single-shot results that were never a conversation. Compounding this, **errored LLM calls are silently counted as safe samples** in every aggregate (ASR, safety_score, robustness, toxicity), so any model with flaky/rate-limited API access mechanically looks safer than it is — and the worst-affected metric path (HuggingFace/custom providers) silently queries OpenAI instead of the named model. On the security side, there is **no ownership model at all**: any self-registered user can read, run, export, or delete every other researcher's evaluations and the shared prompt library (textbook IDOR + missing admin gates). Finally, CI provides false assurance — it runs only 4 of 9 engine test files, the green detector tests pass *only because the ML deps are absent*, and several tests are tautological. **Bottom line:** before any number from this platform enters a paper, the detector/aggregation logic and the authorization model must be fixed; the current metrics are systematically biased toward "safe," non-reproducible across runs, and in some provider/error paths attributed to the wrong model entirely.

---

## 2. Findings by Severity

### Critical (7)

**EV1 / EN1 — [research-validity] Errored LLM responses counted as safe samples in metric denominators** `redteam-engine/core.py:54-155`
Error responses are returned as fully-formed `PromptResult`s (`is_jailbroken=False`, `refusal_detected=False`, toxicity/hallucination `=0.0`) and fed unfiltered into `compute_aggregate_scores`, which divides by `len(results)`. *(EV1 and EN1 are the same defect from two analysis lanes; treat as one.)*
**Impact:** Every error deflates `jailbreak_rate`/ASR and inflates `safety_score = 1 - jailbreak_rate`; a run with 50% API errors reports an artificially safe model. These aggregates are written straight onto the `Evaluation` and `LLMModel` rows and become the paper's headline metrics.
**Fix:** Tag error results and exclude them from `n` and all rates in `compute_aggregate_scores`; surface an `errored_prompts` count instead of hiding the dropped fraction.

**IN1 (integrations) — [research-validity] Factory routes 'huggingface'/'custom' providers to OpenAI with the OpenAI key/endpoint** `backend/integrations/factory.py:15-17`
For `huggingface`/`custom`, the factory builds an `OpenAIClient` with `OPENAI_API_KEY` and the default OpenAI base URL, ignoring the model's `api_endpoint`; `OpenAIClient` never accepts `base_url` either.
**Impact:** Every metric for a HuggingFace/custom model is produced by OpenAI under the wrong model name — published comparison/CWSS rows for those providers are simply false. If `OPENAI_API_KEY` is unset the call errors and is then scored as all-safe (see EV1).
**Fix:** Pass `api_endpoint` into the client and have `OpenAIClient` use `base_url=api_endpoint` (validated non-empty); otherwise raise `ValueError` for unsupported providers rather than silently aliasing to OpenAI.

**DE1 — [research-validity] Toxicity heuristic uses naive substring matching, producing massive false positives** `redteam-engine/detectors/toxicity.py:43-59`
`_score_toxicity_heuristic` flags `kw in text_lower` with no word boundaries, so `die`∈`studied`, `meth`∈`method`, `rape`∈`grape`/`therapeutic`, `hate`∈`whatever`. This is the *only* toxicity path in the default install (detoxify is "optional").
**Impact:** Benign academic responses score as toxic; `toxicity_score` corrupts the per-category vulnerability/exposure profiles and every downstream toxicity figure.
**Fix:** Match whole words via a precompiled `\b(...)\b` regex (or set-membership over tokenized words); handle inflections explicitly, not via accidental substrings.

**DE2 — [research-validity] REFUSAL_INDICATORS contains generic harm words that fire on compliant responses** `redteam-engine/detectors/_constants.py:11-21`
The bare words `harmful`, `unethical`, `inappropriate`, `dangerous` sit alongside real refusal phrases and are matched by substring, so a compliant jailbreak with a safety caveat ("Sure, here's how… note this is dangerous") gets `refusal_count>0`.
**Impact:** Drives both `detect_refusal` and the jailbreak heuristic — compliant jailbreaks get flipped to `mixed_signals`/`refusal_detected`, undercounting jailbreaks while inflating refusal consistency. Both ASR and refusal metrics are biased.
**Fix:** Remove the four standalone words (or restrict to refusal-context phrases), keep only first-person refusal markers, and add word-boundary matching.

**IN2 (integrations) — [research-validity] Celery retry re-runs the whole evaluation and appends a duplicate set of result rows** `workers/tasks/evaluation_task.py:19-39`
`run_evaluation_task` retries on any exception (`max_retries=2`), and `EvalService.run_evaluation` inserts a fresh `EvaluationResult` per prompt with no idempotency guard or prior-row cleanup, so a retry appends a *second* full set of rows (up to 3× on two retries).
**Impact:** The cross-eval CWSS/ASR pool double-counts the retried evaluation's prompts, skewing per-model aggregates toward whichever runs happened to hit transient failures — making paper metrics non-reproducible and infra-dependent.
**Fix:** Make the run idempotent — delete existing `EvaluationResult` rows for the `evaluation_id` (and reset aggregates) before inserting, within one transaction.

**IN1 (infra-ci) — [research-validity] CI engine job runs only 4 of 9 detector/strategy test files** `.github/workflows/ci.yml:72-76`
`test-engine` hard-codes `pytest tests/test_metrics.py tests/test_refusal.py tests/test_core.py`; `test_bias.py`, `test_toxicity.py`, `test_jailbreak.py`, `test_hallucination.py`, `test_strategies.py` are never collected — exactly the files validating the detectors/strategies that produce the published metrics. They parse cleanly and their deps are installed, so they are deliberately omitted, not skipped.
**Impact:** A broken bias/toxicity/jailbreak/hallucination detector or attack strategy ships with a green badge.
**Fix:** Run the whole suite (`pytest tests/ -v --cov=. --cov-report=term`); mark genuinely flaky files with an explicit `@pytest.mark.skip` + reason so any omission is visible.

---

### High (16)

**ME1 — [research-validity] Vulnerability-cluster cosine similarity zips index-misaligned vectors across models tested on different prompts** `redteam-engine/analysis/transfer.py:252-293`
`get_vector` filters to only the prompts a model was tested on, so two models' vectors share length only by coincidence and `zip(v1,v2)` compares model A on prompt p1 against model B on prompt p2. The documented definition requires a fixed shared prompt index.
**Impact:** VCS "vulnerability clusters" can group models that share no measured vulnerability (or split ones that do); any "models X and Y share a safety-training profile" claim is unsupported.
**Fix:** Build vectors over the global ordered prompt set and compute similarity only over the intersection of prompts both models were tested on, with a minimum-overlap guard.

**DE3 — [research-validity] Jailbreak mixed-signals verdict is order/count-fragile and flipped by caveats** `redteam-engine/detectors/jailbreak.py:117-132`
`is_jailbroken = success_count > refusal_count`; because REFUSAL_INDICATORS holds generic harm words (DE2), a compliant "Sure, here's how / Step 1" answer with two caveat words is labeled not-jailbroken. The `expected_behavior=='refusal' and len>200` branch also labels any long benign answer as jailbroken (conf 0.4).
**Impact:** `is_jailbroken` is the numerator of ASR, ASR@k, CWSS, SWHS, and the transfer matrix; verdicts that flip on caveat-word counts make the central metric non-reproducible.
**Fix:** Fix DE2 first; for mixed signals prefer structure (a leading explicit refusal should dominate), require strong first-person refusal markers, and drop the bare `>` tie-breaker.

**DE4 — [research-validity] Hallucination detector flags correctly-formatted real citations/statistics** `redteam-engine/detectors/hallucination.py:23-41`
It only checks for citation-like *formatting* (`et al. (YYYY)`, `doi:`, `NN% of`, "according to a study") and long/`/article/`/`/paper/` URLs — never whether anything is real. A truthful, well-sourced sentence scores `0.6`.
**Impact:** `hallucination_score` measures citation density, which is *anti-correlated* with the intended signal; the `confident_error`/`false_citation` metrics are invalid as published.
**Fix:** Relabel as "citation/claim density," or add real verification (DOI/URL resolution, stat cross-checking) and require corroborating fabrication signals rather than presence-of-format.

**DE6 — [research-validity] semantic-drift endpoint fabricates 'conversations' from independent single-turn results** `redteam-engine/detectors/semantic_drift.py:266-314`
The only production caller (`analytics.py:548-561`) groups *unrelated* single-shot prompt/response pairs sharing an `attack_type`, orders by row id, and feeds them as one dialogue; the detector has no `conversation_id`/`turn_index` guard.
**Impact:** Every metric from `GET /analytics/semantic-drift/{id}` (`drift_score`, `drift_velocity`, `yes_ladder_score`, `commitment_creep_index`, `manipulation_onset_turn`) is meaningless for the headline "first multi-turn manipulation detector" claim.
**Fix:** Require genuine multi-turn provenance (conversation/session id + turn order), reconstruct real Crescendo/PAIR transcripts, and reject input that is not one conversation.

**DE7 — [correctness] Yes-ladder monotonicity uses `>=`/`<=`, so a flat all-zero conversation scores a perfect ladder** `redteam-engine/detectors/semantic_drift.py:211-237`
With non-strict comparisons, a constant (typically all-zero) density series satisfies every step, giving `trend_score = 1.0`.
**Impact:** `yes_ladder_score` saturates to ~1.0 for the most common keyword-free conversations; since `is_drifting` and `drift_score` weight it, drift is systematically over-detected.
**Fix:** Use strict `>`/`<` and require a nonzero change so all-zero sequences score 0.

**ST1 — [research-validity] TAP `depth_reached` undercounts depth when pruning reduces per-depth budget** `redteam-engine/strategies/tap.py:195`
Depth is back-derived as `attempts_used // (beam_width*branching_factor) + 1`, assuming every depth spends the full budget; pruning/reseeding makes later depths cheaper, so executed depths map onto a smaller reported number (empirically 3 depths → reported 2).
**Impact:** A core TAP interpretability metric (RQ3 "does pruning allocate budget well?") is systematically wrong whenever pruning occurs — the normal case.
**Fix:** Track actual depth in the loop (`max(e['depth'] for e in tree_log)+1` or a per-iteration counter) instead of the division estimate.

**BA1 — [security] No ownership model — any authenticated user can read/modify/run/export/delete every other user's data (IDOR)** `backend/api/routes/evaluations.py:93-166`
The `Evaluation` model has no owner column; every route filters by PK only with no `current_user` scoping, and `/auth/register` is open. Attackers enumerate integer ids to read raw prompts/responses, run others' evals (burning API budget), or delete them; `list_evaluations` returns all evaluations to everyone.
**Impact:** Cross-tenant disclosure, tampering, and destruction of research data on a platform whose outputs feed a paper.
**Fix:** Add `user_id` FK to `Evaluation`, set it on create, filter every get/list/run/delete/results route by owner (or admin), and return 404 on ownership failure to avoid enumeration leakage.

**BA2 — [security] Destructive/state-changing routes gated only by `get_current_user`, not admin/owner** `backend/api/routes/evaluations.py:155-166`
`delete_evaluation` uses `get_current_user` while `delete_model` correctly requires `get_current_admin` — the gate was intended but omitted. Same over-permissive gating on `create_model`, the `seed_*`/`delete_attack_prompt` library routes, and `run_evaluation`.
**Impact:** Any self-registered user can wipe others' evaluations, pollute the shared adversarial-prompt library (changing what every eval measures), and burn LLM budget.
**Fix:** Gate destructive/library-mutating routes on `get_current_admin` or an explicit owner check, mirroring `delete_model`.

**EV3 — [reliability] Results persisted only at the very end — a mid-run crash loses all rows** `backend/services/eval_service.py:86-125`
All prompts run before any `EvaluationResult` is added; the only result commit is at line 123. The `on_progress` callback commits `completed_prompts` (advancing the bar) while zero result rows exist, so progress can show "done" with nothing persisted.
**Impact:** A crash/kill/redeploy mid-run loses every result and aggregate while progress falsely reports completion, stranding the eval in `running`; large silent data-loss window for long runs.
**Fix:** Persist each `EvaluationResult` incrementally (per-prompt or every k), compute aggregates only from persisted rows.

**EV4 — [research-validity] Model safety/robustness scores overwritten by the latest run, never aggregated, never decremented on delete** `backend/services/eval_service.py:118-121`
`model.safety_score`/`robustness_score` are set to *this* run's aggregates while `total_evaluations += 1` implies cumulative; a different-`eval_type` run clobbers the previous one, and deletes leave stale scores + inflated counts.
**Impact:** Leaderboard/per-model numbers reflect an arbitrary last (possibly off-type) run, drift out of sync after deletion, and invalidate cross-model comparison.
**Fix:** Compute model scores as an aggregate over completed evals (optionally per `eval_type`) or derive on read; recompute on delete.

**EV5 — [reliability] No row lock / atomic status claim on 'running' — concurrent runs double-count** `backend/api/routes/evaluations.py:124-150`
Classic check-then-act: read `status`, check `!='running'`, later set `'running'` and commit, with no `with_for_update`/atomic UPDATE. Two concurrent runs both pass the guard, duplicating result rows and double-incrementing `total_evaluations`; the sync `EvalService` never re-checks status at all.
**Impact:** Duplicate result rows and doubled counts corrupt any aggregate; reachable via a double-click or retry.
**Fix:** Claim atomically (`UPDATE ... SET status='running' WHERE id=:id AND status!='running'`, proceed only if `rowcount==1`) and re-assert the claim in `EvalService`.

**IN3 (integrations) — [reliability] `EvalService.run_evaluation` is non-atomic; partial commits strand evals in 'running'** `backend/services/eval_service.py:65-123`
Multiple commits (status, progress) happen before any result rows are written; a kill between progress and final commit leaves `status='running'`, `completed_prompts>0`, zero results, no aggregates. The task's except/finally doesn't run on a hard-limit SIGKILL.
**Impact:** Evals stick in `running` and are excluded from completed aggregates, silently shrinking the dataset behind the paper's metrics with no signal.
**Fix:** Insert results incrementally and/or wrap in one transaction; add a startup sweep to fail stale `running` evals; set `task_acks_late` + `task_reject_on_worker_lost`.

**IN4 (integrations) — [reliability] No request timeout on OpenAI/Anthropic clients; hung calls stall the worker pool** `backend/integrations/openai_client.py:27-38`
Neither client sets a timeout; SDK defaults are ~600s. With `worker_concurrency=4`/`prefetch=1`, four hung requests block all slots, and one hung prompt stalls the whole sequential evaluation.
**Impact:** A provider stall hangs the eval until the hard limit kills the worker (stuck `running`, compounds IN3) and collapses throughput for large sweeps.
**Fix:** Pass an explicit per-request `timeout` (e.g. 60s) and `max_retries` to both SDK clients, well under the task budget.

**IN5 (integrations) — [research-validity] API errors return `text=''` and are indistinguishable from a benign empty/refusal response** `backend/integrations/openai_client.py:50-56`
Both clients return `text=""`, `error=str(e)` on any exception; the engine maps that to non-jailbroken/non-refusal/zero-toxicity and still includes it in aggregates. An error mechanically raises `safety_score` and lowers jailbreak/toxicity *and* robustness, distorting the whole metric vector. *(Root-causes EV1/EN1 at the client layer.)*
**Impact:** Rate-limit/timeout storms during a sweep silently fold failed prompts in as "safe," with no visible error in stored metrics.
**Fix:** Propagate an error flag so errored samples are excluded from `n` (and counted separately); refuse to mark an eval `completed` if any prompt errored.

**FR1 — [correctness] Export-CSV link issues a GET to a POST-only, auth-required endpoint — feature is broken** `frontend/src/pages/EvaluationDetail.tsx:59-65`
The export is a plain `<a href={...} download>`, but the backend route is `@router.post("/export/{eval_id}")` behind `get_current_user`/HTTPBearer. A browser navigation is a GET with no `Authorization` header → 405/401/403.
**Impact:** The Export CSV button silently fails for every user; a core data-extraction feature for the paper never works.
**Fix:** Fetch via the authenticated `request()` path with POST + Bearer header, then trigger a client-side Blob download (or change the route to GET with an acceptable auth scheme).

---

### Medium (20)

**DE5 — [research-validity] Bias regex uses unbounded `.*` with DOTALL, flagging cross-sentence co-occurrences** `redteam-engine/detectors/bias.py:103-113`
Patterns like `\b(black|...)\b.*\b(criminal|...)\b` with `DOTALL` span the whole response, so a demographic term in one sentence plus a trigger word anywhere else matches ("Black holes are fascinating… the criminal justice system…").
**Impact:** `has_demographic_bias`/`demographic_score` fire on benign text, inflating per-category bias rates and any BBQ-style result.
**Fix:** Bound the gap (`.{0,80}`, drop DOTALL) or run patterns per-sentence so term and trigger must co-occur in a clause.

**DE8 — [correctness] Refusal and jailbreak are not mutually exclusive — a response can be both** `redteam-engine/core.py:69-83`
The ML jailbreak path and substring `detect_refusal` are computed independently and can both be true (e.g. `is_jailbroken=True` via low refusal-template similarity while a generic word like `harmful` sets `refusal_detected=True`).
**Impact:** Refusal-consistency and ASR derive from contradictory flags on one row; `p_refusal` can exceed the non-jailbreak fraction, making the entropy metric incoherent.
**Fix:** Reconcile through one classifier (e.g. don't report `refusal_detected` from generic words when `is_jailbroken`), and assert mutual exclusivity.

**DE9 — [reliability] `semantic_drift` reloads SentenceTransformer on every pair, unlike cached singletons elsewhere** `redteam-engine/detectors/semantic_drift.py:176-189`
`_semantic_distance` instantiates `SentenceTransformer('all-MiniLM-L6-v2')` on every call (n−1× per conversation, more across attack groups); `jailbreak.py` caches it.
**Impact:** With sentence-transformers installed, the drift endpoint is extremely slow/memory-thrashing and may time out, silently falling back to the Jaccard path — non-deterministic distances between runs.
**Fix:** Cache the model in a module singleton like `jailbreak._get_st_model` and batch-encode all responses once.

**DE10 — [research-validity] Hallucination URL detector double-counts and treats benign long/article URLs as hallucination** `redteam-engine/detectors/hallucination.py:28-36`
Any URL >60 chars or containing `/article/`/`/paper/` adds another 0.15; legitimate news/journal links match. Combined with DE4, a truthful answer citing a real article accrues multiple indicators from formatting alone.
**Impact:** Correctly-sourced answers are penalized as hallucinations, further decoupling the score from ground truth.
**Fix:** Flag only URLs that fail validation (non-resolving/malformed/invented TLD); remove length and `/article/` heuristics.

**ST2 — [research-validity] PAIR `FailureMode.TOO_EXPLICIT` is documented but never produced — taxonomy has 6 active modes, not 7** `redteam-engine/strategies/pair.py:97-126`
`_classify_failure` never returns `TOO_EXPLICIT`; a short explicit refusal hits `EXPLICIT_REFUSAL` first. The mode's refinement operators (lines 188-201) are dead code.
**Impact:** `mode_distribution['too_explicit']` is always 0; the headline PAIR "7-mode Failure Taxonomy" is misrepresented in the API and any mode-histogram figure.
**Fix:** Add a `TOO_EXPLICIT` branch (refusal marker + short + non-moralizing) before the generic return, or remove the mode from the docs to match code.

**EN4 — [research-validity] Generators emit no mutation provenance, breaking the documented genealogy integration and Mutation-Efficiency metric** `redteam-engine/generators.py:126-242`
Variants carry only a `subcategory` suffix — no `mutation_type`/`seed_index` — yet `build_tree_from_generator_output` keys on those, so it attributes every mutation to seed 0 / operator `unknown`. No code actually bridges the two modules.
**Impact:** "Mutation Efficiency per operator" and "most_effective_mutation" (a headline contribution, RQ6) can't be computed from real generator output.
**Fix:** Stamp `mutation_type` and `seed_index` on each variant and add an adapter into the shape the tree builder expects.

**EN6 — [research-validity] `expand_prompts` uses unseeded `random.sample`, making benchmark expansion non-reproducible** `redteam-engine/generators.py:131`
Template selection is unseeded; two identical calls return different variant sets, and `expand_for_benchmark` inherits this.
**Impact:** A "research benchmark" generates different prompts (and metrics) each run, undermining reproducibility of anything built on generator expansion.
**Fix:** Accept an optional seed/RNG (`random.Random(seed)`), default to a fixed seed, and report it with the metrics.

**BA3 — [security] JWT decode doesn't require the `exp` claim — tokens minted without expiry never expire** `backend/services/auth_service.py:44-48`
`jwt.decode` lacks `options={'require':['exp']}`; python-jose only validates `exp` when present, so an exp-less token is valid forever. The HS256 allowlist correctly mitigates algorithm confusion, but with no refresh/revocation this is a real gap.
**Impact:** Any exp-less token grants permanent access; combined with BA1/BA2 a single long-lived token is high value.
**Fix:** Decode with `options={'require':['exp'],'verify_exp':True}`; optionally require `sub`.

**BA4 — [reliability] Rate limiter keys on `request.client.host` (the proxy IP behind any reverse proxy) and is per-process/unbounded** `backend/main.py:46-67`
No `X-Forwarded-For`/trusted-proxy handling, so behind a proxy the whole user base shares one bucket (self-DoS); naive XFF trust would let attackers spof unlimited buckets. State is in-process (resets on restart, not shared across workers) and `_rate_buckets` grows unboundedly.
**Impact:** Brute-force protection on `/auth/login` collapses to one shared bucket (availability) or is weakened ×worker_count; slow memory leak; inconsistent enforcement at scale.
**Fix:** Resolve the real client IP via trusted-proxy middleware; move state to a shared store (Redis) with TTL eviction.

**EV7 — [correctness] Missing `ON DELETE CASCADE`/ORM cascade — deleting a model orphans evaluations; FK unenforced under SQLite** `backend/models/evaluation.py:29-48`
Relationships declare no `cascade` and FKs no `ondelete`; `delete_model` calls `db.delete(model)` with no cleanup. On SQLite (`foreign_keys` pragma off) the delete succeeds and orphans rows; on PostgreSQL it hard-fails. Behavior diverges by backend.
**Impact:** Orphaned evaluations/results (stats then sum over dangling FKs) under SQLite, or undeletable models under Postgres.
**Fix:** Add `cascade='all, delete-orphan'` + `ondelete='CASCADE'` (model + migration) and enable `PRAGMA foreign_keys=ON` in `database.py`.

**IN6 (integrations) — [reliability] No rate-limit/backoff in LLM clients; bare `except` swallows the error type** `backend/integrations/anthropic_client.py:49-55`
Retryable (`RateLimitError`/`APITimeout`/5xx) and permanent (bad key/model) errors are all flattened to `error=str(e)` with no retry/`Retry-After`. The only retry is Celery's, which re-runs the entire eval (IN2) and never fires here because client errors are returned as data, not raised.
**Impact:** Under rate limiting (expected in sweeps), many prompts fail and are scored benign (IN5) with no per-call recovery — lossy and biased, invisible in stored metrics.
**Fix:** Catch provider-specific retryable exceptions and back off honoring `Retry-After` (or enable SDK `max_retries`); reserve the error path for permanent failures and propagate the distinction.

**IN8 (integrations) — [reliability] Celery not configured for `acks_late`/`reject_on_worker_lost`; a killed worker drops the task** `workers/celeryconfig.py:14-19`
With default early-ack, the message is acked on receipt; a kill mid-run loses it with no redelivery, leaving the eval in IN3's partial state. `result_expires` is also unset (unbounded Redis retention).
**Impact:** Long/over-limit runs or worker restarts silently lose evals (eval stuck `running`, compounds IN3), quietly shrinking the dataset; unbounded result retention.
**Fix:** Set `task_acks_late=True` + `task_reject_on_worker_lost=True` (safe once idempotent per IN2), set `result_expires`, and reconcile stale `running` evals on startup.

**FR2 — [reliability] Expired/invalid JWT is never detected — user is trapped in a logged-in UI where every call 401s** `frontend/src/services/api.ts:15-39`
`isAuthenticated()` only checks token presence, not validity; `request()` throws a generic error on non-OK and never inspects 401 or calls `clearToken()`. After expiry the app shell renders but every fetch fails.
**Impact:** Post-expiry the authenticated app is non-functional with no auto re-login; users perceive it as broken until they manually sign out.
**Fix:** Special-case 401 in `request()` (`clearToken()` + reload/logout); optionally decode `exp` client-side.

**FR3 — [correctness] Adaptive Budget panel renders 'NaN%' when the backend returns an insufficient-data object** `frontend/src/pages/Research.tsx:312-337`
The backend returns HTTP 200 with `{"error": "Insufficient data…"}`; the panel only routes rejected promises to the error card, so a 200 with an `error` field sets `data`, and `data.simulation?.mean_adaptive_asr * 100` becomes `undefined*100 = NaN`.
**Impact:** On a common sparse-data path, the research panel shows fabricated-looking "NaN%" instead of an explanation — misleading in a results UI feeding a paper.
**Fix:** In `.then`, if `data.error` set the error and clear data; guard the render and the multiplication with `?? 0`.

**FR4 — [security] JWT stored in `localStorage` — readable by any injected/third-party script (XSS token theft)** `frontend/src/services/api.ts:3-26`
The bearer JWT lives in `localStorage` and is attached manually; any XSS or malicious dependency can exfiltrate a long-lived token. The backend already sets `allow_credentials=True`, suggesting cookie auth was anticipated.
**Impact:** One XSS/supply-chain compromise yields a token authorizing all operations until expiry — meaningful for a platform holding sensitive adversarial data.
**Fix:** Move the token to an `httpOnly`, `Secure`, `SameSite` cookie set on login; if `localStorage` stays, keep lifetimes short and add CSP.

**IN2 (infra-ci) — [security] All application containers run as root (no `USER` directive)** `infrastructure/docker/backend/Dockerfile:1-16`
None of the backend/frontend/worker Dockerfiles drop privileges, so every process runs as uid 0; compose bind-mounts the host source into the container, so an RCE in the eval path (which by design ingests hostile prompts/model output) runs as root and can write back to host source.
**Impact:** Container breakout / host-source tampering surface is amplified for a platform whose job is processing hostile input; pushed GHCR images also default to root.
**Fix:** Add a non-root `USER` after install/COPY in each Dockerfile and align uid for bind-mounted dev volumes.

**IN3 (infra-ci) — [reliability] Compose worker builds the backend Dockerfile, not the dedicated worker Dockerfile — compose and CI/CD images diverge** `docker-compose.yml:87-102`
The worker service builds `backend/Dockerfile` (which only `COPY . .` from `./backend`, never baking `workers/`/`redteam-engine/`), papered over by runtime bind mounts; the GHCR `llm-redteam-worker` image is built from `worker/Dockerfile`, exercised by nobody in dev.
**Impact:** The production worker image is never validated locally; a missing COPY/dep passes all local testing and only fails at deploy. Inconsistent build provenance.
**Fix:** Point the worker service at `infrastructure/docker/worker/Dockerfile` with context `.`, matching `docker.yml`.

**TE2 — [research-validity] Toxicity test asserts keyword strings only the heuristic can produce** `redteam-engine/tests/test_toxicity.py:11-18`
`test_toxic_text` asserts `'kill'`/`'murder'` ∈ `flagged_terms`, which only the heuristic populates; the ML path sets category names, so the test is tautological vs. the heuristic and guaranteed to fail under the shipped ML detector. It never checks the score.
**Impact:** False confidence — confirms keywords echo back, never validates the `toxicity_score` that feeds `avg_toxicity`/the vulnerability profile, and is incompatible with the production detector.
**Fix:** Assert on `toxicity_score` thresholds and make the `flagged_terms` assertion branch-aware; add a mocked-Detoxify test for the ML branch.

**TE3 — [reliability] Engine detector suite is environment-fragile: green only because the pinned ML deps are absent** `redteam-engine/tests/conftest.py:1-42`
Nothing pins which detector implementation runs; pass/fail of `test_jailbreak`/`test_toxicity`/`test_core`/parts of `test_strategies` depends on whether `sentence-transformers`/`detoxify` happen to be importable (they aren't on the dev box). No marker/`importorskip`/monkeypatch makes the path deterministic.
**Impact:** Non-reproducible results undercut the stated "reproducible benchmarking" goal; the same commit can go red in a properly provisioned CI, so the green badge isn't a trustworthy signal.
**Fix:** Force a known backend per test (monkeypatch `_ml_available` for heuristic tests; stub the ML model for ML tests) and document the intended backend.

**TE4 — [security] No test asserts cross-user isolation on evaluations — the IDOR path is entirely uncovered** `backend/tests/test_evaluations.py:52-77`
Every test authenticates as one seeded user against an owner-less `Evaluation`; there is no "user B is denied user A's eval" case (expected 403/404).
**Impact:** A core authorization property is silently untested, so the green suite hides the BA1 cross-tenant exposure/deletion vector. *(Verifier confidence: medium — the test-suite gap is the defect; root cause is BA1.)*
**Fix:** Add a second user/token and tests asserting 403/404 on GET/delete/results/run of another user's eval (they will fail until ownership is enforced — the desired signal).

---

### Low (10)

**ME2 — [research-validity] Standalone CWSS and refusal-consistency return 0.0 for empty input, contradicting the aggregator's 'safe when no data' convention** `redteam-engine/analysis/metrics.py:139-162`
`confidence_weighted_safety_score([])` and `refusal_consistency_score([])` return 0.0 ("maximally unsafe") while `compute_all_metrics([])` hard-codes `cwss=1.0`/`refusal_consistency=1.0`.
**Impact:** A model with zero usable results (e.g. all API calls errored) is rank-ordered as the *least* safe in any comparison touching the standalone function, inverting safety leaderboards.
**Fix:** Make both paths agree on empty input (return 1.0, or return None/NaN and exclude no-data models from rankings).

**ME4 — [research-validity] `build_tree_from_generator_output` flattens all mutations to generation 1** `redteam-engine/analysis/genealogy.py:323-361`
This documented integration path attaches every mutation directly to its seed (`parent_id = seed_ids[seed_idx]`), so all nodes are gen 1; the output dict carries no parent-mutation id, so multi-step lineage can't be expressed.
**Impact:** "Generational Fitness Gain" and "Shortest Successful Chain" via this path are structurally capped at depth 1, so they can't answer the stated minimum-mutation-depth question. *(Core `add_mutation` supports deeper chains; this path isn't wired into the backend yet, limiting live impact.)*
**Fix:** Carry a parent id through generator output and use it to set true parents, or document the depth-1 limitation to avoid over-claiming.

**DE11 — [research-validity] Drift `info_disclosure_rate` scaled by an arbitrary ×10 factor, distorting `drift_score`** `redteam-engine/detectors/semantic_drift.py:343-352`
A per-word density (~0.001–0.02) is multiplied by 10 then weighted 0.10, uncapped until the final sum; high sensitive-keyword density alone contributes up to 0.10 independent of any cross-turn drift, and the evidence threshold (0.001) fires on noise.
**Impact:** `drift_score` (used for sorting and `is_drifting`) is partly driven by static sensitive-word density, biasing the novel metric and per-category drift ranking.
**Fix:** Compute disclosure as a cross-turn trend (late − early density), clamp the contribution, and raise the evidence threshold above noise.

**ST3 — [research-validity] Crescendo `escalation_steps_executed` reports the planned count, not steps actually run** `redteam-engine/strategies/crescendo.py:189`
The field is `len(escalation_steps)` (planned); an early break on success means fewer ran, but the full planned length is still reported (depth-5 success on turn 1 → reports 5). No field records actual steps.
**Impact:** "Turns-to-jailbreak"/multi-turn-dynamics analysis (RQ2) can't distinguish a turn-1 success from a 5-step run.
**Fix:** Increment a per-iteration counter (or read `tree_log`) and report that; keep `escalation_steps_planned` separately if wanted.

**ST4 — [research-validity] Crescendo records single-turn prompt text as `jailbreak_found`, losing multi-turn provenance** `redteam-engine/strategies/crescendo.py:150-169`
`jailbreak_found` is set to only the triggering turn's text, but the jailbreak is a function of the full accumulated conversation; `_detect_jailbreak` is even called with only `step_prompt`. The full trace survives in `all_prompts/all_responses`, but downstream consumers read `jailbreak_found`.
**Impact:** Genealogy/transfer analyses and the write-up attribute multi-turn successes to a single benign-looking turn, misrepresenting which prompt elicited the unsafe output.
**Fix:** Store the serialized conversation up to the triggering turn (or add `jailbreak_turn_index` + full message list).

**EN3 — [research-validity] Dataset severity values fall outside the per-family ranges documented in the README** `redteam-engine/datasets/adversarial_prompts.py:223-667`
11 prompts violate the documented ranges (e.g. bias_probing racial-ranking = `critical`; hallucination `fabricated_citation`/`false_consensus` = `high`; robustness ANFO-typo/methamphetamine-completion = `critical`).
**Impact:** SWHS and per-family severity reporting won't match the documented taxonomy; reviewers reproducing the README's severity distribution get different numbers.
**Fix:** Either widen the README ranges to the real distribution or re-classify the out-of-range prompts.

**EN5 — [maintainability] `redteam-engine/config.py` is a dead, duplicated detector lexicon that can silently drift from `_constants.py`** `redteam-engine/config.py:1-42`
The file duplicates all detector lexicons and claims "all detectors import from this file," but every detector imports from `detectors/_constants.py`; `config.py` is imported by nothing.
**Impact:** Latent trap — an author tuning the lexicon in the file the docstring points to changes nothing, a likely future wrong-results regression.
**Fix:** Delete `config.py`, or make it re-export from `_constants.py` so they can't diverge.

**BA5 — [reliability] Auth bodies accept any string; bcrypt silently truncates passwords to 72 bytes** `backend/api/routes/auth.py:14-23`
`email`/`password` are bare `str` (no `EmailStr`, no length/strength), and bcrypt truncates to 72 bytes, so longer passwords are accepted but only the first 72 bytes verify; no upper bound on input length.
**Impact:** Junk-email accounts, silently weakened long passwords, no minimum length — an input-validation gap on the security-critical auth surface.
**Fix:** Use `EmailStr`, `Field(min_length=8, max_length=128)`, and pre-hash (e.g. SHA-256) before bcrypt so truncation can't weaken verification.

**EV8 — [reliability] N+1: stats endpoint loads every completed evaluation into Python to average four floats** `backend/api/routes/evaluations.py:175-191`
`evaluation_stats` pulls every completed `Evaluation` ORM object (all columns incl. JSON config) just to compute averages in Python on a hot endpoint.
**Impact:** Dashboard latency/memory grow linearly with evaluation count; full-table materialization on every hit.
**Fix:** Replace with a single `func.avg(...)` aggregate query.

**EV9 — [research-validity] Per-result `hallucination_score` is computed but never stored — only the aggregate survives** `backend/models/evaluation.py:33-48`
`PromptResult` carries `hallucination_score`, but `EvaluationResult` has no such column, so the store loop never persists it; only the run-level `hallucination_rate` remains.
**Impact:** Per-prompt hallucination signal is discarded, preventing drill-down into which prompts induced hallucinations for the paper.
**Fix:** Add a `hallucination_score` column (model + migration) and store `r.hallucination_score` in the insert loop.

**EV10 — [maintainability] Schema drift: `updated_at` ORM-only `onupdate` and missing indexes on hot filter columns** `backend/alembic/versions/001_initial_schema.py:45-63`
`updated_at` relies on a Python-side `onupdate` (no DB trigger), so non-ORM/bulk writes never refresh it; and `model_id`, `status`/`eval_type`, and `evaluation_results.evaluation_id` have no indexes, making every status filter and per-eval result lookup a full scan.
**Impact:** Unreliable `updated_at` for non-ORM writes; O(table) result fetches/status filters as the dataset grows.
**Fix:** Add `index=True` to the FK/filtered columns (ORM + migration); accept `updated_at` as ORM-maintained or add a DB trigger.

**FR5 — [reliability] Delete handlers have no error handling — admin-only model delete fails silently for non-admins** `frontend/src/pages/Models.tsx:31-35`
`handleDelete` awaits `api.deleteModel(id)` with no try/catch; `DELETE /models/{id}` requires admin and raises 403, so the promise rejects unhandled, `load()` never runs, and the Delete button is shown to everyone. Same pattern in `Evaluations.tsx`.
**Impact:** Non-admins see a Delete control that throws an unhandled rejection with no feedback and no refresh — confusing, inconsistent with backend authz.
**Fix:** Wrap in try/catch and surface `err.message`; ideally hide/disable Delete for non-admins via an exposed admin flag.

**IN4 (infra-ci) — [reliability] CI lint suppresses F401 and runs no frontend lint or unit tests** `.github/workflows/ci.yml:19-22`
`ruff --ignore=E501,E402,F401` hides unused/broken imports (a real correctness signal given the engine's module-level re-exports); the frontend pipeline does only `tsc --noEmit`/`build` with no eslint and no `npm test`/vitest.
**Impact:** Broken/dead imports in the metric-producing engine pass lint; the results-display frontend has no behavioral gate, so wrong-metric-mapping bugs ship unnoticed.
**Fix:** Drop F401 from the ignore list; add a frontend test job (vitest) and eslint.

**IN5 (infra-ci) — [reliability] GHCR images tagged `latest` and no healthchecks on backend/worker/frontend** `.github/workflows/docker.yml:41-43`
Each image is tagged both `:latest` and `:${sha}`; deploying `latest` makes "which image produced these numbers" ambiguous. Compose's backend/worker/frontend define no healthcheck, and frontend `depends_on: [backend]` waits only for container start.
**Impact:** Reproducibility risk for an academic artifact; frontend can come up against a not-ready backend. *(Low — the sha tag is also published and compose is dev-oriented.)*
**Fix:** Pin deploys to the sha tag (restrict `latest` to default-branch); add a backend healthcheck and `depends_on: condition: service_healthy`.

**TE5 — [research-validity] ASR@k math has untested edges and an aliased-object empirical fixture** `redteam-engine/tests/test_metrics.py:88-110`
`asr_at_k` is never tested with empty results or `k=0`; `empirical_asr_at_k` uses `[make_result(...)]*3` (one shared object ×3); and `group[:k]` for `k` > group length is never asserted.
**Impact:** The probabilistic ASR@k formula and empirical group-slicing — both reported in the paper — could regress (off-by-one in `group[:k]`, wrong `k=0`) with no test failing; the aliased fixture risks future false-greens.
**Fix:** Add `asr_at_k([], k)` and `asr_at_k(results, 0)` tests; build empirical groups with fresh objects via comprehension; add a `k`-exceeds-length and a success-at-index-`k` boundary case.

---

### Info (1)

**ME3 — [reliability] `asr_at_k` raises `ZeroDivisionError` for non-positive `k`** `redteam-engine/analysis/metrics.py:77-90`
`1.0 - (1.0 - asr)**k` with `asr==0.0` and `k<0` raises `ZeroDivisionError`; `k==0` silently returns a meaningless 0.0. Callers currently hardcode `k∈{3,5,10}`, so impact is latent.
**Impact:** A bad `k` from future config/API exposure crashes metric generation with an opaque error.
**Fix:** Validate `k` at the top (`if k <= 0: raise ValueError(...)`), documenting the contract.

---

## 3. Cross-Cutting Themes

1. **Detectors measure surface form, not meaning — the root research-validity failure.** DE1 (substring toxicity), DE2/DE3 (generic harm words as refusal/jailbreak signal), DE4/DE10 (citation *formatting* as hallucination), DE5 (cross-sentence regex), DE11 (raw keyword density as drift) all share one flaw: they pattern-match tokens with no boundaries, proximity, semantics, or verification. Several are *anti-correlated* with their intended signal (a careful, well-sourced, caveated answer scores as more toxic, more refusing, and more hallucinatory).

2. **Errors and empty input are silently scored as "safe."** EV1/EN1/IN5 fold failed API calls into the denominator as non-jailbroken/zero-toxicity; ME2 ranks a no-data model as least-safe via the standalone function; FR3 shows NaN on the insufficient-data path. The system has no consistent "no data" semantics, and the default ("safe") biases every headline metric toward favorable results precisely when infrastructure is failing.

3. **Reported counts/metrics drift from what actually executed.** ST1 (TAP depth from a budget division), ST3 (planned vs. executed escalation steps), ST4 (single-turn provenance for a multi-turn attack), EN4/ME4 (lost mutation lineage), EV4 (last-run scores masquerading as cumulative) all report a *modeled or planned* number instead of the *observed* one — corrupting exactly the interpretability metrics the paper's research questions depend on.

4. **No object-level authorization anywhere.** BA1 (no owner column / IDOR), BA2 (missing admin gates), BA3 (non-expiring tokens), FR4 (token in localStorage), BA5 (no input validation), and TE4 (untested isolation) compose into: open registration → unscoped global data → long-lived, XSS-exposed tokens → no test catching it. Any registered user can read/run/delete all research data and the shared prompt library.

5. **Durability/idempotency gaps make runs lossy and non-reproducible.** IN2 (retry duplicates rows), EV3/IN3 (results persisted only at the end; partial commits strand evals in `running`), EV5 (no atomic status claim), IN4/IN6/IN8 (no timeouts/backoff/redelivery), EV7 (no cascade) form a chain where transient provider/infra failures silently corrupt or lose the dataset behind the metrics.

6. **CI and tests provide false assurance.** IN1-ci (4 of 9 test files run), TE3 (green only because ML deps are absent), TE2 (tautological, ML-incompatible assertions), TE4/TE5 (uncovered authz and ASR@k edges), IN4-ci (F401 suppressed, no frontend tests) mean a green badge does **not** establish that the detectors, the math, or the authorization model are correct.

7. **Provider/config mis-routing produces wrong-model and divergent-artifact results.** IN1-integrations (HF/custom → OpenAI), IN3-ci (compose worker ≠ shipped worker image), IN5-ci (`latest` tag), EN5/EV10 (duplicated lexicon, schema drift) all break the link between "what is named/documented" and "what actually ran."

---

## 4. Recommended Remediation Order

Fix research-validity and security before anything cosmetic. Within those, fix root causes that many other findings depend on first.

1. **Stop counting errors/empty as "safe" (EV1/EN1, IN5, ME2).** This is the single change that most corrupts every aggregate. Tag errored `PromptResult`s, exclude them from `n`/all rates, surface an `errored_prompts` count, and align the standalone CWSS/refusal-consistency empty-input convention with `compute_all_metrics`. Until this lands, *no aggregate is trustworthy*.

2. **Fix the provider-routing lie (IN1-integrations).** A wrong-model metric is worse than a missing one. Honor `api_endpoint` or raise for unsupported providers, so HF/custom rows aren't silently OpenAI.

3. **Decouple and bound the detector lexicons / matching (DE2 → DE1, DE3, DE5, DE10, DE4, DE11, DE7).** Fix DE2 first (it feeds DE3 and DE8), add word-boundary/proximity matching, and either add real verification or relabel the hallucination/drift metrics. These produce the paper's core numbers.

4. **Establish object-level authorization (BA1 → BA2, BA3, then FR4/BA5, with TE4 as the regression test).** Add an owner column + per-route ownership/admin filters, require `exp` on tokens, then harden token storage and input validation. Add the cross-user isolation tests so it can't silently regress.

5. **Make runs idempotent and durable (IN2 → EV5, EV3/IN3, IN8; then IN4/IN6).** Make `run_evaluation` delete-then-insert under one transaction (idempotent), claim `running` atomically, persist results incrementally, add timeouts/backoff/redelivery, and a stale-`running` startup sweep — *in that order* (idempotency must precede enabling `acks_late` redelivery).

6. **Restore CI as a real signal (IN1-ci, TE3, TE2, IN4-ci).** Run the full engine suite, force a deterministic detector backend, fix the tautological toxicity test, drop F401 and add frontend tests — so the fixes above are actually guarded going forward.

7. **Correct the "planned vs. executed" reporting (ST1, ST3, ST4, EN4/ME4, EV4).** Report observed depth/steps/provenance and aggregate (not last-run) model scores, so the interpretability figures match reality.

8. **Then the rest:** broken Export CSV (FR1), trapped-on-expiry UI (FR2), NaN panel (FR3), silent delete (FR5); reproducibility/ops hygiene (EN6, EN3, EN5, EV7/EV9/EV10, EV8, BA4, IN2-ci/IN3-ci/IN5-ci); and the latent edge-case guards (TE5, ME3).

---

**Note on coverage:** This report reflects the 57 findings that survived adversarial verification; all but one (TE4, medium confidence) were rated high-confidence by the verifier. Where two findings describe the same defect from different lanes (EV1/EN1, and IN5 as their client-layer root cause), they are noted as such rather than double-counted as independent issues.
