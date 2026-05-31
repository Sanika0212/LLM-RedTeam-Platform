"""Celery task for running evaluations in the background."""

import sys
import os
import logging

# Ensure backend code is importable
backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from workers.eval_worker import app
from database import SessionLocal
from services.eval_service import EvalService
from models.evaluation import Evaluation

logger = logging.getLogger(__name__)


@app.task(bind=True, name="run_evaluation", max_retries=2)
def run_evaluation_task(self, evaluation_id: int):
    """Run an evaluation asynchronously via Celery."""
    db = SessionLocal()
    try:
        logger.info(f"Starting evaluation {evaluation_id}")
        service = EvalService(db)
        service.run_evaluation(evaluation_id)
        logger.info(f"Evaluation {evaluation_id} completed successfully")
    except Exception as exc:
        logger.error(f"Evaluation {evaluation_id} failed: {exc}")
        # Mark evaluation as failed
        evaluation = (
            db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
        )
        if evaluation and evaluation.status != "completed":
            evaluation.status = "failed"
            db.commit()
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
