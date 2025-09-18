"""
Online Assessment Router.
Handles OA endpoints with date validation.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict
from controller.oa_controller import get_oa_page, submit_oa_answers

router = APIRouter()


class OASubmission(BaseModel):
    answers: Dict[str, str]


@router.get("/{candidate_id}/OA/{process_id}", response_class=HTMLResponse)
async def online_assessment_page(candidate_id: str, process_id: str):
    """
    Display online assessment page.
    URL format: /candidate_id/OA/process_id
    """
    return await get_oa_page(candidate_id, process_id)


@router.post("/{candidate_id}/OA/{process_id}/submit")
async def submit_online_assessment(candidate_id: str, process_id: str, submission: OASubmission):
    """
    Submit online assessment answers and get score.
    """
    return await submit_oa_answers(candidate_id, process_id, submission.answers)