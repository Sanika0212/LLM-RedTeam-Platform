import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class LLMModel(Base):
    __tablename__ = "llm_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    provider = Column(String(100), nullable=False)  # openai, anthropic, huggingface, custom
    model_id = Column(String(255), nullable=False)  # e.g. gpt-4, claude-3-opus
    description = Column(Text, default="")
    api_endpoint = Column(String(500), default="")
    safety_score = Column(Float, default=0.0)
    robustness_score = Column(Float, default=0.0)
    total_evaluations = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    evaluations = relationship("Evaluation", back_populates="model")
