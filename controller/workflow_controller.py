"""
Controller for workflow functionality.
Handles all business logic related to workflow management and scheduling.
"""

import asyncio
from fastapi import HTTPException
from typing import List, Dict, Any
from workflow.resume_scoring.resume_shortlisting_workflow import run_resume_scoring_workflow
from workflow.assessment_workflow import process_assessment_results, bulk_update_assessment_scores
from workflow.interview_workflow import process_interview_results, bulk_update_interview_scores


async def trigger_resume_workflow(process_id: str):
    """
    Manually trigger the resume shortlisting workflow for a specific process.
    This includes email notifications to candidates.
    """
    try:
        # Add timeout to prevent hanging on Render
        result = await asyncio.wait_for(
            run_resume_scoring_workflow(process_id), 
            timeout=30.0
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Workflow timeout - process may still be running")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger resume workflow: {str(e)}")


async def trigger_assessment_workflow(process_id: str, assessment_results: List[Dict[str, Any]]):
    """
    Process online assessment results and send email notifications.
    
    Args:
        process_id: The hiring process ID
        assessment_results: List of {"candidate_id": str, "score": int}
    """
    try:
        result = await process_assessment_results(process_id, assessment_results)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process assessment results: {str(e)}")


async def trigger_interview_workflow(process_id: str, interview_results: List[Dict[str, Any]]):
    """
    Process offline interview results and send email notifications.
    
    Args:
        process_id: The hiring process ID
        interview_results: List of {"candidate_id": str, "tech_score": int, "hr_score": int}
    """
    try:
        result = await process_interview_results(process_id, interview_results)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process interview results: {str(e)}")


# Utility functions for testing
async def bulk_test_assessment(process_id: str):
    """
    Bulk update assessment scores for testing purposes.
    """
    try:
        result = await bulk_update_assessment_scores(process_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk test assessment: {str(e)}")


async def bulk_test_interview(process_id: str):
    """
    Bulk update interview scores for testing purposes.
    """
    try:
        result = await bulk_update_interview_scores(process_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk test interview: {str(e)}")


# Legacy function for backward compatibility
async def trigger_workflow(process_id: str):
    """
    Legacy function - redirects to resume workflow.
    """
    return await trigger_resume_workflow(process_id)


async def get_scheduler_status():
    """Get current scheduler status."""
    try:
        from workflow.resume_scoring.polling_scheduler import get_scheduler_status
        return await get_scheduler_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


async def reset_scheduler():
    """Reset scheduler state (useful for testing)."""
    try:
        from workflow.resume_scoring.polling_scheduler import reset_scheduler
        await reset_scheduler()
        return {"message": "Scheduler state reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset scheduler: {str(e)}")



async def get_workflow_status(process_id: str):
    """Get the current status of all candidates in a process."""
    try:
        from db_manager import db_manager
        from bson import ObjectId
        
        applications = await db_manager.get_collection("applications")
        candidates = await db_manager.get_collection("candidate")
        
        status_summary = {
            "Applied": 0,
            "Resume_shortlisted": 0,
            "Resume_rejected": 0,
            "OA_cleared": 0,
            "OA_rejected": 0,
            "Interview_cleared": 0,
            "Interview_rejected": 0
        }
        
        candidate_details = []
        
        async for app in applications.find({"process_id": process_id}):
            status = app.get("status", "Applied")
            if status in status_summary:
                status_summary[status] += 1
            
            # Get candidate name
            candidate = await candidates.find_one({"_id": ObjectId(app["candidate_id"])})
            candidate_name = candidate.get("name", "Unknown") if candidate else "Unknown"
            
            candidate_details.append({
                "candidate_id": app["candidate_id"],
                "candidate_name": candidate_name,
                "status": status,
                "resume_score": app.get("resume_match_score"),
                "oa_score": app.get("oa_score"),
                "tech_score": app.get("tech_score"),
                "hr_score": app.get("hr_score")
            })
        
        return {
            "process_id": process_id,
            "status_summary": status_summary,
            "total_candidates": sum(status_summary.values()),
            "candidate_details": candidate_details
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")
