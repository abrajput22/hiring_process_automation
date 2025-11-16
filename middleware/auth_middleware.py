from fastapi import HTTPException, Depends, Cookie
from typing import Optional
import json
import jwt
import os

class User:
    def __init__(self, email: str, role: str, user_id: str):
        self.email = email
        self.role = role
        self.user_id = user_id

async def get_current_user(user_data: Optional[str] = Cookie(None), token: Optional[str] = Cookie(None)) -> User:
    """Read user data from cookie and validate token"""
    if not user_data or not token:
        raise HTTPException(status_code=401, detail="Please login")
    
    # Check if token is expired
    try:
        secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
        jwt.decode(token, secret, algorithms=["HS256"])  # This will raise exception if expired
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired, please login again")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Parse user data
    try:
        # Handle base64 encoded user data
        import base64
        decoded_data = base64.b64decode(user_data).decode('utf-8')
        data = json.loads(decoded_data)
        return User(data["email"], data["role"], data["candidate_id"])
    except:
        # Fallback: try parsing without base64 decode
        try:
            data = json.loads(user_data)
            return User(data["email"], data["role"], data["candidate_id"])
        except:
            raise HTTPException(status_code=401, detail="Invalid user data")

async def require_candidate(user: User = Depends(get_current_user)) -> User:
    """Only candidates allowed"""
    if user.role != "candidate":
        raise HTTPException(status_code=403, detail="Candidates only")
    return user

async def require_hr(user: User = Depends(get_current_user)) -> User:
    """Only HR allowed"""
    if user.role != "hr":
        raise HTTPException(status_code=403, detail="HR only")
    return user


