"""Authentication and authorization dependencies."""

from api.deps.auth import get_current_admin, get_current_user

__all__ = ["get_current_user", "get_current_admin"]
