"""Authentication service — JWT token management and password hashing."""

import hashlib
import hmac
from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its hash.

    Supports both bcrypt ($2b$ prefix) and legacy SHA-256 (salt$hash) hashes.
    """
    if hashed.startswith(("$2b$", "$2a$")):
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    # Legacy SHA-256 fallback
    if "$" not in hashed:
        return False
    salt, pw_hash = hashed.split("$", 1)
    check = hashlib.sha256(f"{salt}:{plain}".encode()).hexdigest()
    return hmac.compare_digest(check, pw_hash)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
