from fastapi import APIRouter

from api.routes import auth, models, evaluations, attack_prompts, analytics

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
api_router.include_router(attack_prompts.router, prefix="/attack-prompts", tags=["attack-prompts"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
