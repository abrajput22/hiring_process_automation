from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class Candidate(BaseModel):
    """
    Pydantic model representing the candidate identity and profile.
    Resume text is now stored per-application in the Application model.
    """
    name: Optional[str] = None
    email: EmailStr
    password: Optional[str] = None  # stored as-is for now; hash in production
    role: Optional[str] = None

class Application(BaseModel):
    """
    Pydantic model for tracking individual applications.
    Each candidate can have multiple applications to different processes.
    Each application has its own resume text.
    """
    candidate_id: str
    process_id: str
    resume_text: Optional[str] = None  # Resume text specific to this application
    status: Optional[str] = "Applied"
    resume_match_score: Optional[int] = None
    oa_score: Optional[int] = None
    tech_score: Optional[int] = None
    hr_score: Optional[int] = None
    final_score: Optional[float] = None  # Combined weighted score for final selection
    created_at: Optional[datetime] = None 
    updated_at: Optional[datetime] = None
    
class HiringProcess(BaseModel):
    """
    Pydantic model for a hiring process managed by HR.
    """
    hr_id: str
    hr_email: str
    company_id: str
    process_name: str
    job_description: str
    resume_deadline: datetime
    assessment_date: datetime
    offline_interview_date: datetime
    package_offered: str

class User(BaseModel):
    """
    Pydantic model for user authentication and roles.
    """
    email: EmailStr
    password: str
    role: str  # e.g., 'HR' or 'candidate'

class AssessmentQuestion(BaseModel):
    """
    Pydantic model for a single multiple-choice question.
    """
    question: str
    options: List[str]
    answer: str
