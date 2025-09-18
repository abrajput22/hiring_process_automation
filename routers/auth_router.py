from fastapi import APIRouter, Response
from fastapi.responses import FileResponse
from datetime import datetime, timedelta, timezone
import jwt
import os
import json
import base64
 
from controller.auth_controller import handle_signup, handle_login, UserCreate, UserLogin

def _view_path(filename: str) -> str:
    return os.path.join(os.path.dirname(__file__), "..", "views", filename)

router = APIRouter()

# Auth API endpoints
@router.post("/signup")  # Called by: Signup form | Returns: New user registration confirmation
async def api_signup(user_data: UserCreate):
    return await handle_signup(user_data)

@router.post("/login")  # Called by: Login form | Returns: JWT token in cookie + user data
async def api_login(user_data: UserLogin, response: Response):
    user = await handle_login(user_data)

    jwt_secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
    jwt_algo = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_exp_minutes = int(os.getenv("JWT_EXPIRES_MIN", "60"))

    candidate_id = getattr(user, "candidate_id", None)

    payload = {
        "sub": user.email,
        "role": user.role,
        "candidate_id": candidate_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=jwt_exp_minutes),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, jwt_secret, algorithm=jwt_algo)
    
    user_data = {"email": user.email, "role": user.role, "candidate_id": candidate_id}
    encoded_user_data = base64.b64encode(json.dumps(user_data).encode()).decode()

    # Set cookies with automatic expiration
    response.set_cookie(
        key="token",
        value=token,
        max_age=jwt_exp_minutes * 60,
        httponly=False,
        secure=False,
        samesite="lax",
        path="/",
        domain=None
    )
    response.set_cookie(
        key="user_data",
        value=encoded_user_data,
        max_age=jwt_exp_minutes * 60,
        httponly=False,
        secure=False,
        samesite="lax",
        path="/",
        domain=None
    )

    return {
        "message": "Login successful",
        "user": user_data
    }

@router.post("/logout")  # Called by: Logout button | Returns: Cookie deletion confirmation
async def api_logout(response: Response):
    response.delete_cookie(key="token", path="/")
    response.delete_cookie(key="user_data", path="/")
    return {"message": "Logged out successfully"}

# Auth pages
@router.get("/login")  # Called by: Browser navigation | Returns: Login HTML form
async def serve_login_page():
    return FileResponse(_view_path("login.html"))

@router.get("/signup")  # Called by: Browser navigation | Returns: Signup HTML form
async def serve_signup_page():
    return FileResponse(_view_path("signup.html"))

@router.get("/test-navbar")  # Called by: Debug test | Returns: Navbar test HTML
async def serve_test_navbar():
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "test_navbar_simple.html"))