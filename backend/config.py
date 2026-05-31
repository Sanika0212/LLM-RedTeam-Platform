import os
import secrets
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

logger = logging.getLogger(__name__)

_WEAK_KEYS = {
    "dev-secret-key-change-in-production",
    "your-secret-key-change-in-production",
    "changeme",
    "secret",
}


class Settings:
    PROJECT_NAME: str = "LLM Red-Team Platform"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Database - fallback to SQLite if no PostgreSQL URL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'llm_redteam.db'}"
    )

    # Redis (optional for dev)
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")
    )

    # LLM API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Model defaults
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-4")
    MAX_CONCURRENT_EVALS: int = int(os.getenv("MAX_CONCURRENT_EVALS", "5"))

    # CORS
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]

    def __init__(self) -> None:
        if not self.SECRET_KEY or self.SECRET_KEY in _WEAK_KEYS:
            if not self.DEBUG:
                raise ValueError(
                    "SECRET_KEY is missing or insecure. "
                    "Set a strong SECRET_KEY environment variable for production."
                )
            self.SECRET_KEY = secrets.token_urlsafe(32)
            logger.warning(
                "SECRET_KEY not set — generated an ephemeral key for debug mode. "
                "Tokens will not survive restarts."
            )


settings = Settings()
