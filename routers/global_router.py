from fastapi import APIRouter, Depends, Cookie
from fastapi.responses import FileResponse, RedirectResponse
import os
from typing import Optional

from controller.process_controller import list_hiring_processes
from controller.workflow_controller import get_scheduler_status, reset_scheduler
from middleware.auth_middleware import User, get_current_user

def _view_path(filename: str) -> str:
    return os.path.join(os.path.dirname(__file__), "..", "views", filename)

router = APIRouter()

# Root and home
@router.get("/")  # Called by: Browser root access | Returns: Redirect to home page
async def root():
    return RedirectResponse(url="/home")

@router.get("/home")  # Called by: Browser navigation | Returns: Main home HTML page
async def serve_home_page():
    return FileResponse(_view_path("home.html"))

# Global endpoints
@router.get("/processes")  # Called by: Home page JS | Returns: List of all available processes
async def get_all_processes():
    return await list_hiring_processes()

@router.get("/processes/{process_id}")  # Called by: Process detail JS | Returns: Specific process details
async def get_process_detail_global(process_id: str):
    from controller.process_controller import get_process_detail
    return await get_process_detail(process_id)

# Scheduler endpoints
@router.get("/scheduler/status")  # Called by: Admin dashboard | Returns: Scheduler health status
async def get_scheduler_status_endpoint():
    return await get_scheduler_status()

@router.post("/scheduler/reset")  # Called by: Admin reset button | Returns: Scheduler reset confirmation
async def reset_scheduler_endpoint():
    return await reset_scheduler()

@router.get("/validate-token")  # Called by: Frontend JS | Returns: Token validity and user info
async def validate_token_endpoint(user: User = Depends(get_current_user)):
    return {"valid": True, "user_id": user.user_id, "role": user.role, "email": user.email}

@router.get("/auth-status")  # Called by: Navbar JS | Returns: Current auth status without requiring auth
async def get_auth_status(token: Optional[str] = Cookie(None)):
    """Check auth status without throwing errors"""
    if not token:
        return {"authenticated": False}
    
    try:
        import jwt
        secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
        data = jwt.decode(token, secret, algorithms=["HS256"])
        return {
            "authenticated": True,
            "user_id": data["candidate_id"],
            "role": data["role"],
            "email": data["sub"]
        }
    except:
        return {"authenticated": False}