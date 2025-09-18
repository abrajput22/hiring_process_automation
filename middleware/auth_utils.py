"""
Authentication utilities and helper functions.
Provides convenient decorators and utilities for JWT authentication.
"""

from functools import wraps
from typing import Callable, Any
from fastapi import Depends
from .auth_middleware import User, get_current_user, require_candidate, require_hr


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require JWT authentication for a function.
    Usage:
        @require_auth
        async def my_endpoint(user: User = Depends(get_current_user)):
            return {"user": user.email}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def require_candidate_auth(func: Callable) -> Callable:
    """
    Decorator to require candidate authentication for a function.
    Usage:
        @require_candidate_auth
        async def my_endpoint(user: User = Depends(require_candidate)):
            return {"candidate_id": user.candidate_id}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def require_hr_auth(func: Callable) -> Callable:
    """
    Decorator to require HR authentication for a function.
    Usage:
        @require_hr_auth
        async def my_endpoint(user: User = Depends(require_hr)):
            return {"hr_user": user.email}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


# Common dependency combinations
def get_authenticated_user() -> User:
    """Get any authenticated user (candidate or HR)."""
    return Depends(get_current_user)


def get_authenticated_candidate() -> User:
    """Get authenticated candidate user."""
    return Depends(require_candidate)


def get_authenticated_hr() -> User:
    """Get authenticated HR user."""
    return Depends(require_hr)
