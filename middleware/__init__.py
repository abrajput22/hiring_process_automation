"""
Middleware package for the hiring process application.
Contains authentication and other middleware components.
"""

from .auth_middleware import (
    User,
    get_current_user,
    require_candidate,
    require_hr
)

__all__ = [
    "User",
    "get_current_user",
    "require_candidate",
    "require_hr"
]
