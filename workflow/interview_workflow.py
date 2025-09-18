"""
Offline Interview Workflow with Email Notifications.
Handles scoring and email notifications for offline interviews.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from db_manager import db_manager
from bson import ObjectId
from workflow.email_notifications.email_service import notify_interview_results


async def process_interview_results(process_id: str, interview_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process offline interview results and send email notifications.
    
    Args:
        process_id: The hiring process ID
        interview_results: List of interview results with candidate_id, tech_score, and hr_score
    
    Returns:
        Dict with processing results and email notification status
    """
    try:
        # Get process data
        processes = await db_manager.get_collection("Processes")
        process_data = await processes.find_one({"_id": ObjectId(process_id)})
        
        if not process_data:
            return {"error": "Process not found"}
        
        # Get applications and candidates
        applications = await db_manager.get_collection("applications")
        candidates = await db_manager.get_collection("candidate")
        
        updated_candidates = []
        update_count = 0
        
        for result in interview_results:
            candidate_id = result["candidate_id"]
            tech_score = result.get("tech_score", 0)
            hr_score = result.get("hr_score", 0)
            
            # Calculate overall interview score (weighted average)
            overall_score = (tech_score * 0.7) + (hr_score * 0.3)
            
            # Determine status based on overall score (threshold: 70)
            new_status = "Interview_cleared" if overall_score >= 70 else "Interview_rejected"
            
            # Update application in database
            update_result = await applications.update_one(
                {
                    "candidate_id": candidate_id,
                    "process_id": process_id
                },
                {
                    "$set": {
                        "tech_score": tech_score,
                        "hr_score": hr_score,
                        "status": new_status,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            if update_result.modified_count > 0:
                update_count += 1
                
                # Get candidate details for email
                candidate = await candidates.find_one({"_id": ObjectId(candidate_id)})
                if candidate:
                    updated_candidates.append({
                        "_id": candidate_id,
                        "name": candidate.get("name"),
                        "email": candidate.get("email"),
                        "tech_score": tech_score,
                        "hr_score": hr_score,
                        "overall_score": overall_score,
                        "status": new_status
                    })
        
        # Send email notifications
        process_name = process_data.get("process_name", "Unknown Position")
        email_results = await notify_interview_results(updated_candidates, process_name)
        
        return {
            "status": "success",
            "total_processed": len(interview_results),
            "updated_count": update_count,
            "cleared_count": len([c for c in updated_candidates if c["status"] == "Interview_cleared"]),
            "rejected_count": len([c for c in updated_candidates if c["status"] == "Interview_rejected"]),
            "email_notifications": {
                "sent": email_results["sent"],
                "failed": email_results["failed"],
                "details": email_results["details"]
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to process interview results: {str(e)}"
        }


async def bulk_update_interview_scores(process_id: str, score_threshold: int = 70) -> Dict[str, Any]:
    """
    Bulk update interview scores for all candidates who cleared the assessment.
    This is a utility function for testing or batch processing.
    """
    try:
        # Get all applications for this process with OA_cleared status
        applications = await db_manager.get_collection("applications")
        cleared_apps = []
        
        async for app in applications.find({
            "process_id": process_id,
            "status": "OA_cleared"
        }):
            cleared_apps.append(app)
        
        if not cleared_apps:
            return {"message": "No candidates cleared assessment for interview"}
        
        # Simulate interview results (in real scenario, this would come from interview system)
        import random
        interview_results = []
        
        for app in cleared_apps:
            # Generate random scores for simulation
            tech_score = random.randint(40, 95)
            hr_score = random.randint(50, 90)
            
            interview_results.append({
                "candidate_id": app["candidate_id"],
                "tech_score": tech_score,
                "hr_score": hr_score
            })
        
        # Process the results
        return await process_interview_results(process_id, interview_results)
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to bulk update interview scores: {str(e)}"
        }