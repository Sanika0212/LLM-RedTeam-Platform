"""Evaluation service — orchestrates running evaluations against LLMs."""

import sys
import os
import datetime

from sqlalchemy.orm import Session

# Add redteam-engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "redteam-engine"))

from models.evaluation import Evaluation, EvaluationResult
from models.llm_model import LLMModel
from models.attack_prompt import AttackPrompt
from integrations.factory import get_llm_client
from core import RedTeamEngine


class EvalService:
    """Handles the full lifecycle of running an evaluation."""

    def __init__(self, db: Session):
        self.db = db

    def run_evaluation(self, evaluation_id: int) -> Evaluation:
        """
        Run a full evaluation: fetch prompts, call the LLM, score responses,
        store results, and update aggregate scores.
        """
        evaluation = (
            self.db.query(Evaluation)
            .filter(Evaluation.id == evaluation_id)
            .first()
        )
        if not evaluation:
            raise ValueError("Evaluation not found")

        model = (
            self.db.query(LLMModel)
            .filter(LLMModel.id == evaluation.model_id)
            .first()
        )
        if not model:
            raise ValueError("Model not found")

        # Get attack prompts — filter by eval type, fallback to all
        prompts = (
            self.db.query(AttackPrompt)
            .filter(AttackPrompt.category == evaluation.eval_type)
            .all()
        )
        if not prompts:
            prompts = self.db.query(AttackPrompt).all()
        if not prompts:
            raise ValueError(
                "No attack prompts available. Seed prompts first via "
                "POST /api/v1/attack-prompts/seed"
            )

        # Build LLM client — config errors (bad provider/missing endpoint) mark the
        # evaluation failed immediately rather than leaving it stuck in 'pending'.
        try:
            llm_client = get_llm_client(
                model.provider, model.model_id, model.api_endpoint or ""
            )
        except ValueError as e:
            evaluation.status = "failed"
            self.db.commit()
            raise ValueError(f"Model configuration error: {e}") from e

        # Mark as running
        evaluation.status = "running"
        evaluation.total_prompts = len(prompts)
        evaluation.completed_prompts = 0
        self.db.commit()

        # Build engine and run
        engine = RedTeamEngine(llm_client)
        prompt_dicts = [
            {
                "prompt": p.prompt,
                "category": p.category,
                "expected_behavior": p.expected_behavior or "refusal",
            }
            for p in prompts
        ]

        def on_progress(completed, total):
            evaluation.completed_prompts = completed
            self.db.commit()

        try:
            results = engine.run_evaluation(prompt_dicts, on_progress=on_progress)
        except Exception as e:
            evaluation.status = "failed"
            self.db.commit()
            raise ValueError(f"Evaluation failed: {str(e)}")

        # Idempotency: delete any prior result rows for this evaluation so Celery
        # retries don't double-count (IN2).
        self.db.query(EvaluationResult).filter(
            EvaluationResult.evaluation_id == evaluation.id
        ).delete()

        # Persist only non-errored results (R2). Errored prompts are tracked in
        # aggregates["errored_prompts"] and recorded on the Evaluation row, but
        # storing them as EvaluationResult rows would pollute analytics queries
        # that group/sum over results without an is_error filter.
        for r in results:
            if r.is_error:
                continue
            db_result = EvaluationResult(
                evaluation_id=evaluation.id,
                prompt=r.prompt,
                response=r.response,
                attack_type=r.attack_type,
                is_jailbroken=1 if r.is_jailbroken else 0,
                toxicity_score=r.toxicity_score,
                coherence_score=r.coherence_score,
                refusal_detected=1 if r.refusal_detected else 0,
                extra_data=r.extra_data,
            )
            self.db.add(db_result)

        # Compute aggregate scores (errored calls excluded from denominators)
        aggregates = RedTeamEngine.compute_aggregate_scores(results)
        evaluation.jailbreak_rate = aggregates["jailbreak_rate"]
        evaluation.hallucination_rate = aggregates["hallucination_rate"]
        evaluation.completed_at = datetime.datetime.utcnow()
        evaluation.completed_prompts = aggregates["valid_prompts"]

        # Set final status: failed if every prompt errored, completed otherwise (R3/IN5)
        if aggregates["valid_prompts"] == 0:
            evaluation.status = "failed"
            evaluation.safety_score = 0.0
            evaluation.robustness_score = 0.0
        else:
            evaluation.status = "completed"
            evaluation.safety_score = aggregates["safety_score"]
            evaluation.robustness_score = aggregates["robustness_score"]
            # Only update model-level scores when we have valid results (R7)
            model.total_evaluations += 1
            model.safety_score = aggregates["safety_score"]
            model.robustness_score = aggregates["robustness_score"]

        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation
