from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.llm_model import LLMModel
from models.user import User
from api.deps import get_current_user, get_current_admin

router = APIRouter()


class ModelCreate(BaseModel):
    name: str
    provider: str
    model_id: str
    description: str = ""
    api_endpoint: str = ""


class ModelResponse(BaseModel):
    id: int
    name: str
    provider: str
    model_id: str
    description: str
    safety_score: float
    robustness_score: float
    total_evaluations: int

    class Config:
        from_attributes = True


@router.get("/", response_model=list[ModelResponse])
def list_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(LLMModel).all()


@router.post("/", response_model=ModelResponse, status_code=201)
def create_model(
    model: ModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(LLMModel).filter(LLMModel.name == model.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Model with this name already exists")
    db_model = LLMModel(**model.model_dump())
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


@router.get("/{model_id}", response_model=ModelResponse)
def get_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.delete("/{model_id}", status_code=204)
def delete_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    db.delete(model)
    db.commit()
