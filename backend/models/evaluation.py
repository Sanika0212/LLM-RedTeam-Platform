import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from database import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    model_id = Column(Integer, ForeignKey("llm_models.id"), nullable=False)
    eval_type = Column(String(100), nullable=False)  # safety, robustness, accuracy, jailbreak
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    config = Column(JSON, default=dict)
    total_prompts = Column(Integer, default=0)
    completed_prompts = Column(Integer, default=0)
    safety_score = Column(Float, default=0.0)
    robustness_score = Column(Float, default=0.0)
    jailbreak_rate = Column(Float, default=0.0)
    hallucination_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    model = relationship("LLMModel", back_populates="evaluations")
    results = relationship("EvaluationResult", back_populates="evaluation")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, default="")
    attack_type = Column(String(100), default="")  # injection, jailbreak, toxicity, etc.
    is_jailbroken = Column(Integer, default=0)  # 0 or 1
    toxicity_score = Column(Float, default=0.0)
    coherence_score = Column(Float, default=0.0)
    refusal_detected = Column(Integer, default=0)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    evaluation = relationship("Evaluation", back_populates="results")
