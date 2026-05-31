# LLM Evaluation & Red-Teaming Platform

A research-grade platform for systematically evaluating and red-teaming Large Language Models (LLMs) through adversarial testing, multi-turn attack strategies, automated jailbreak/bias detection, and rigorous quantitative analysis.

> **Status:** v1.0.0 Research — complete implementation
> **Academic context:** CS research project, adversarial ML / AI safety evaluation

---

## Research Contributions

This platform implements and extends methods from recent LLM safety literature:

| Component | Reference |
|---|---|
| Attack Success Rate (ASR) | Standard metric in red-teaming evaluations |
| ASR@k | Probabilistic multi-shot coverage metric |
| Empirical ASR@k | Per-intent empirical estimate across k attempts |
| Confidence-Weighted Safety Score (CWSS) | Confidence-adjusted penalty metric |
| Refusal Consistency Score | Entropy-based behavioral consistency measure |
| Crescendo attack | Russinovich et al. (2024), Microsoft Research |
| TAP (Tree of Attacks with Pruning) | Mehrotra et al. (2023), arXiv:2312.02119 |
| Bias detection | Gallegos et al. (2023); Parrish et al. (2022) BBQ |
| Hallucination patterns | Regex + suspicious citation detection |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React + TypeScript)            │
│  Dashboard | Evaluations | Analytics | Leaderboard          │
│  Vulnerability Heatmap | Model Comparison | Timeline        │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API (JWT-authenticated)
┌────────────────────────┴────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│  Evaluations | Models | Attack Prompts | Analytics          │
│  CSV Export  | Rate Limiting | Async Tasks                  │
└───┬──────────────────────────────────────────────────────────┘
    │
┌───▼──────────────────────────────────────────────────────────┐
│                   Red-Team Engine                            │
│                                                              │
│  datasets/           — 65+ curated adversarial prompts       │
│  detectors/          — jailbreak · hallucination · bias      │
│  strategies/         — Crescendo · TAP (beam search)        │
│  generators.py       — mutation · encoding · register        │
│  analysis/           — metrics · structured reports         │
│  tests/              — pytest suite for all modules          │
└──────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
llm-redteam-platform/
├── backend/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py              # JWT authentication
│   │       ├── models.py            # LLM model registry
│   │       ├── evaluations.py       # Evaluation CRUD + run
│   │       ├── attack_prompts.py    # Prompt library + seed endpoints
│   │       └── analytics.py        # 7 analytics/reporting endpoints
│   ├── models/                      # SQLAlchemy ORM models
│   ├── services/
│   │   └── eval_service.py         # Full evaluation pipeline
│   └── main.py                      # FastAPI app + rate limiting
│
├── redteam-engine/
│   ├── core.py                      # RedTeamEngine orchestrator
│   ├── generators.py               # Mutation · encoding · register variants
│   │
│   ├── datasets/
│   │   └── adversarial_prompts.py  # 65+ curated prompts, 6 attack families
│   │
│   ├── detectors/
│   │   ├── jailbreak.py            # ML + heuristic hybrid detector
│   │   ├── hallucination.py        # Regex + citation pattern detector
│   │   ├── bias.py                 # Demographic · political · sycophancy
│   │   └── _constants.py           # Shared lexicons
│   │
│   ├── strategies/
│   │   ├── base.py                 # Abstract AttackStrategy + StrategyResult
│   │   ├── crescendo.py            # Multi-turn escalation (Russinovich 2024)
│   │   └── tap.py                  # Tree of Attacks with Pruning (Mehrotra 2023)
│   │
│   ├── analysis/
│   │   ├── metrics.py              # ASR · ASR@k · CWSS · exposure · vulnerability
│   │   └── report.py               # JSON + Markdown report generation
│   │
│   └── tests/
│       ├── test_metrics.py         # 10 test classes, all metric functions
│       ├── test_bias.py            # Bias detector — demographic/political/sycophancy
│       └── test_strategies.py      # Crescendo + TAP with mock LLM clients
│
└── frontend/
    └── src/
        └── pages/
            ├── Dashboard.tsx        # Stats overview + charts
            ├── Evaluations.tsx      # Evaluation management
            ├── EvaluationDetail.tsx # Per-prompt results + CSV export
            ├── Models.tsx           # Model registry
            ├── Leaderboard.tsx      # Rankings + RadarChart
            ├── AttackPrompts.tsx    # Prompt browser + import
            └── Analytics.tsx       # Vulnerability heatmap + model comparison
```

---

## Attack Taxonomy

The platform organizes adversarial prompts into six primary families:

| Family | Subcategories | Severity Range |
|---|---|---|
| `jailbreak` | dan, persona, developer_mode, context_override | medium–critical |
| `injection` | system_override, admin_injection, delimiter | high–critical |
| `safety` | weapon_synthesis, dangerous_info, dual_use | high–critical |
| `bias_probing` | racial, gender, political, sycophancy | medium–high |
| `hallucination` | false_citation, confabulation, confident_error | low–medium |
| `robustness` | token_manipulation, boundary_test, format_exploit | low–medium |

Each prompt carries: category, subcategory, severity, description, expected\_behavior, and tags.

---

## Metrics Reference

| Metric | Definition |
|---|---|
| **ASR** | `|jailbreaks| / |prompts|` |
| **ASR@k** | `1 - (1 - ASR)^k` — probability of ≥1 jailbreak in k attempts |
| **Empirical ASR@k** | Fraction of intents where any of k attempts succeeded |
| **Exposure Rate** | Fraction of harmful queries receiving long non-refusal responses |
| **CWSS** | `1 - mean(is_jailbroken × confidence)` — confidence-penalized safety |
| **Refusal Consistency** | `1 - H(p_refusal) / H_max` — entropy-based behavioral uniformity |
| **Severity-Weighted Harm** | ASR weighted by per-category severity weight |
| **Vulnerability Profile** | Per-category ASR + toxicity + refusal breakdown |

---

## Attack Strategies

### Crescendo (multi-turn escalation)
Maintains a conversation history and progressively escalates from a benign opening toward the target harmful intent. Exploits conversational momentum and recency bias. Supports configurable attack families (cyber, weapons, drugs, social\_engineering, generic) and automatic recovery prompts after refusals.

### TAP (Tree of Attacks with Pruning)
Implements beam search over a tree of adversarial prompt mutations. At each depth, generates `branching_factor` mutations per beam node, scores responses, prunes low-scoring branches, and retains the top-K candidates. Provides a full tree log for interpretability.

---

## Running Tests

```bash
cd redteam-engine
pip install pytest

# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_metrics.py -v
pytest tests/test_bias.py -v
pytest tests/test_strategies.py -v
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

### Red-Team Engine

```bash
cd redteam-engine
pip install pytest
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Access

| Service | URL |
|---|---|
| Dashboard | http://localhost:5173 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## API Reference (selected endpoints)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/login` | JWT login |
| GET/POST | `/api/v1/models` | Model registry |
| GET/POST | `/api/v1/evaluations` | Evaluation CRUD |
| POST | `/api/v1/evaluations/{id}/run` | Run evaluation (async or sync) |
| GET | `/api/v1/attack-prompts` | Browse prompt library |
| POST | `/api/v1/attack-prompts/seed` | Seed 15-prompt starter set |
| POST | `/api/v1/attack-prompts/seed-research-dataset` | Import 65-prompt research dataset |
| GET | `/api/v1/analytics/vulnerability-profile` | Per-category ASR breakdown |
| GET | `/api/v1/analytics/model-comparison` | CWSS-ranked model table |
| GET | `/api/v1/analytics/evaluation-report/{id}` | Full structured report |
| GET | `/api/v1/analytics/category-heatmap` | Model × category ASR matrix |
| GET | `/api/v1/analytics/timeline` | Metrics over time |
| POST | `/api/v1/analytics/export/{eval_id}` | Download results as CSV |

---

## Research Questions

1. **Attack Effectiveness:** Which adversarial families achieve the highest ASR across model families?
2. **Multi-Turn Dynamics:** Does Crescendo's escalation outperform single-shot jailbreaks?
3. **Beam Search Coverage:** Does TAP's pruning effectively allocate budget toward promising branches?
4. **Behavioral Consistency:** Do models that refuse consistently differ from those that are unpredictably inconsistent?
5. **Bias Transfer:** Do bias elicitation prompts that succeed on one model transfer to others?
6. **Confidence Calibration:** Is model confidence (where available) a reliable predictor of jailbreak severity?

---

## Technology Stack

| Layer | Technology |
|---|---|
| API | FastAPI, SQLAlchemy, Alembic, JWT, Celery |
| DB | PostgreSQL, Redis |
| ML | sentence-transformers (lazy-loaded), detoxify (optional) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| Testing | pytest |
| Container | Docker + Docker Compose |

---

## Contributors

- **Sanika:** Backend platform, REST API, frontend dashboard, infrastructure
- **Vaishak:** Red-team engine, attack strategies, evaluation metrics, research components

---

**License:** MIT
