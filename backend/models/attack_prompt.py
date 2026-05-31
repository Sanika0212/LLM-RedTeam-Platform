import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, JSON

from database import Base


class AttackPrompt(Base):
    __tablename__ = "attack_prompts"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)  # injection, jailbreak, toxicity, misinformation
    subcategory = Column(String(100), default="")
    prompt = Column(Text, nullable=False)
    severity = Column(String(50), default="medium")  # low, medium, high, critical
    description = Column(Text, default="")
    expected_behavior = Column(String(100), default="refusal")  # refusal, safe_response
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
