from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

from controller.applied_processes import get_applied_processes
from controller.candidate_profile import get_candidate_profile, update_candidate_profile
from controller.resume_controller import submit_resume, upload_resume_file
from middleware.auth_middleware import User, require_candidate
from db_schema import Candidate

class ProfileUpdate(BaseModel):
    name: Optional[str] = None

def _view_path(filename: str) -> str:
    return os.path.join(os.path.dirname(__file__), "..", "views", filename)

router = APIRouter()

# Resume endpoints (candidate-only)
class ResumeSubmission(BaseModel):
    name: Optional[str] = None
    email: str
    process_id: Optional[str] = None

@router.post("/{candidate_id}/submit-resume")  # Called by: Candidate resume form | Returns: Resume submission confirmation
async def submit_resume_endpoint(candidate_id: str, submission: ResumeSubmission, user: User = Depends(require_candidate)):
    candidate_data = Candidate(
        name=submission.name,
        email=submission.email
    )
    return await submit_resume(candidate_id, candidate_data, user, submission.process_id)

@router.post("/{candidate_id}/upload-resume")  # Called by: Candidate file upload | Returns: File upload success with extracted text length
async def upload_resume_endpoint(candidate_id: str, name: str = Form(default=None), file: UploadFile = File(...), process_id: str = Form(default=None), user: User = Depends(require_candidate)):
    return await upload_resume_file(candidate_id, name, file, user, process_id)

# Applied processes API
@router.get("/api/{candidate_id}/applied-processes")  # Called by: Candidate dashboard | Returns: List of processes candidate applied to
async def get_applied_processes_endpoint(candidate_id: str, user: User = Depends(require_candidate)):
    return await get_applied_processes(candidate_id, user)

# Application scores API
@router.put("/api/{candidate_id}/application/{process_id}/scores")  # Called by: Candidate test submission | Returns: Updated scores confirmation
async def update_application_scores_endpoint(candidate_id: str, process_id: str, scores: dict, user: User = Depends(require_candidate)):
    from controller.application_controller import update_application_scores
    return await update_application_scores(candidate_id, process_id, scores, user)

@router.get("/api/{candidate_id}/application/{process_id}/scores")  # Called by: Candidate results page | Returns: Candidate's test scores and status
async def get_application_scores_endpoint(candidate_id: str, process_id: str, user: User = Depends(require_candidate)):
    from controller.application_controller import get_application_scores
    return await get_application_scores(candidate_id, process_id)



# Profile endpoints
@router.get("/{user_id}/me")  # Called by: Candidate profile page | Returns: Candidate's profile data
async def get_user_me(user_id: str, user: User = Depends(require_candidate)):
    return await get_candidate_profile(user_id, user)

@router.put("/{user_id}/me")  # Called by: Candidate profile update | Returns: Profile update confirmation
async def update_user_me(user_id: str, payload: ProfileUpdate, user: User = Depends(require_candidate)):
    return await update_candidate_profile(user_id, payload, user)

# HTML pages
@router.get("/{candidate_id}/apply")  # Called by: Browser navigation | Returns: Resume upload HTML page
async def serve_apply_page(candidate_id: str):
    return FileResponse(_view_path("resume.html"))

@router.get("/{candidate_id}/profile")  # Called by: Browser navigation | Returns: Candidate profile HTML page
async def serve_profile_page(candidate_id: str):
    return FileResponse(_view_path("profile.html"))

@router.get("/{candidate_id}/applied-processes")  # Called by: Browser navigation | Returns: Applied processes HTML page
async def serve_applied_processes_page(candidate_id: str):
    return FileResponse(_view_path("applied_processes.html"))

@router.get("/{candidate_id}/home")  # Called by: Browser navigation | Returns: Candidate home HTML page
async def serve_home_page_with_id(candidate_id: str):
    return FileResponse(_view_path("home.html"))