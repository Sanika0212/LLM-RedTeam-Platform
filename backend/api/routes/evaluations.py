import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.evaluation import Evaluation, EvaluationResult
from models.llm_model import LLMModel
from models.attack_prompt import AttackPrompt
from models.user import User
from api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class EvaluationCreate(BaseModel):
    name: str
    description: str = ""
    model_id: int
    eval_type: str = "safety"  # safety, robustness, jailbreak, accuracy
    config: dict = {}


class EvaluationResultResponse(BaseModel):
    id: int
    prompt: str
    response: str
    attack_type: str
    is_jailbroken: int
    toxicity_score: float
    coherence_score: float
    refusal_detected: int

    class Config:
        from_attributes = True


class EvaluationResponse(BaseModel):
    id: int
    name: str
    description: str
    model_id: int
    eval_type: str
    status: str
    total_prompts: int
    completed_prompts: int
    safety_score: float
    robustness_score: float
    jailbreak_rate: float
    hallucination_rate: float
    created_at: datetime.datetime | None = None
    completed_at: datetime.datetime | None = None

    class Config:
        from_attributes = True


@router.get("/", response_model=list[EvaluationResponse])
def list_evaluations(
    status: str | None = None,
    eval_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Evaluation)
    if status:
        query = query.filter(Evaluation.status == status)
    if eval_type:
        query = query.filter(Evaluation.eval_type == eval_type)
    return query.order_by(Evaluation.created_at.desc()).all()


@router.post("/", response_model=EvaluationResponse, status_code=201)
def create_evaluation(
    eval_in: EvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = db.query(LLMModel).filter(LLMModel.id == eval_in.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    evaluation = Evaluation(**eval_in.model_dump())
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


@router.get("/{eval_id}", response_model=EvaluationResponse)
def get_evaluation(
    eval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation


@router.get("/{eval_id}/results", response_model=list[EvaluationResultResponse])
def get_evaluation_results(
    eval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return db.query(EvaluationResult).filter(EvaluationResult.evaluation_id == eval_id).all()


@router.post("/{eval_id}/run", response_model=EvaluationResponse)
def run_evaluation(
    eval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run an evaluation — tries Celery async first, falls back to synchronous."""
    evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if evaluation.status == "running":
        raise HTTPException(status_code=400, detail="Evaluation is already running")

    # Try async via Celery worker
    try:
        from workers.tasks.evaluation_task import run_evaluation_task

        run_evaluation_task.delay(eval_id)
        evaluation.status = "running"
        db.commit()
        db.refresh(evaluation)
        logger.info(f"Evaluation {eval_id} dispatched to Celery worker")
        return evaluation
    except Exception as celery_err:
        logger.info(
            f"Celery unavailable ({celery_err}), running evaluation synchronously"
        )

    # Fallback: run synchronously
    from services.eval_service import EvalService

    service = EvalService(db)
    try:
        return service.run_evaluation(eval_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{eval_id}", status_code=204)
def delete_evaluation(
    eval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    db.query(EvaluationResult).filter(EvaluationResult.evaluation_id == eval_id).delete()
    db.delete(evaluation)
    db.commit()


@router.get("/stats/summary")
def evaluation_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get summary statistics across all evaluations."""
    total = db.query(Evaluation).count()
    completed = db.query(Evaluation).filter(Evaluation.status == "completed").count()
    evals = db.query(Evaluation).filter(Evaluation.status == "completed").all()

    avg_safety = sum(e.safety_score for e in evals) / len(evals) if evals else 0
    avg_jailbreak = sum(e.jailbreak_rate for e in evals) / len(evals) if evals else 0
    avg_robustness = sum(e.robustness_score for e in evals) / len(evals) if evals else 0

    return {
        "total_evaluations": total,
        "completed_evaluations": completed,
        "average_safety_score": round(avg_safety, 4),
        "average_jailbreak_rate": round(avg_jailbreak, 4),
        "average_robustness_score": round(avg_robustness, 4),
        "total_models": db.query(LLMModel).count(),
        "total_attack_prompts": db.query(AttackPrompt).count(),
    }
