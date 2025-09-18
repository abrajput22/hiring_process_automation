"""
Controller for applied processes functionality.
Handles all business logic related to candidate applied processes.
"""

from fastapi import HTTPException, Depends
from bson import ObjectId
from db_manager import db_manager
from middleware.auth_middleware import User


async def get_applied_processes(candidate_id: str, user: User):
    """Get all processes that a candidate has applied to."""
    
    applications = await db_manager.get_collection("applications")
    processes = await db_manager.get_collection("Processes")
    
    applied_processes = []
    
    # Get all applications for this candidate
    application_records = await applications.find({"candidate_id": candidate_id}).to_list(None)
    
    for app_record in application_records:
        try:
            process = await processes.find_one({"_id": ObjectId(app_record["process_id"])})
            if process:
                process["_id"] = str(process["_id"])
                process["application_status"] = app_record.get("status", "Applied")
                process["resume_match_score"] = app_record.get("resume_match_score")
                process["oa_score"] = app_record.get("oa_score")
                process["tech_score"] = app_record.get("tech_score")
                process["hr_score"] = app_record.get("hr_score")
                process["applied_date"] = app_record.get("created_at")
                applied_processes.append(process)
        except Exception:
            continue
    
    return {
        "candidate_id": candidate_id,
        "applied_processes": applied_processes,
        "total_applications": len(applied_processes)
    }
