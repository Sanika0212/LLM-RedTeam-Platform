import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import init_db
from api import api_router

# Import all models so metadata is populated for both Alembic and create_all
import models.llm_model  # noqa: F401
import models.evaluation  # noqa: F401
import models.attack_prompt  # noqa: F401
import models.user  # noqa: F401

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ---------------------------------------------------------------------------
# In-memory rate limiter middleware
# ---------------------------------------------------------------------------
_rate_buckets: dict[str, list[float]] = {}

AUTH_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register"}
AUTH_RATE_LIMIT = 10       # requests per window
GENERAL_RATE_LIMIT = 60   # requests per window
RATE_WINDOW = 60.0         # seconds


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    is_auth = path in AUTH_PATHS
    limit = AUTH_RATE_LIMIT if is_auth else GENERAL_RATE_LIMIT
    bucket_key = f"{client_ip}:{'auth' if is_auth else 'general'}"

    now = time.time()
    timestamps = _rate_buckets.get(bucket_key, [])
    # Prune old entries
    timestamps = [t for t in timestamps if now - t < RATE_WINDOW]

    if len(timestamps) >= limit:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again later."},
        )

    timestamps.append(now)
    _rate_buckets[bucket_key] = timestamps
    return await call_next(request)


app.include_router(api_router, prefix=settings.API_PREFIX)


@app.on_event("startup")
def on_startup():
    if settings.DEBUG:
        # Dev mode: auto-create tables for convenience
        init_db()
    else:
        # Production: expect Alembic migrations (run `alembic upgrade head`)
        logger.info("Production mode — skipping auto-create. Use Alembic migrations.")


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "api": settings.API_PREFIX,
    }
