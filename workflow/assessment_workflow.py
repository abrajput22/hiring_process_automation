"""
Online Assessment Workflow with Email Notifications.
Handles scoring and email notifications for online assessments.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from db_manager import db_manager
from bson import ObjectId
from workflow.email_notifications.email_service import notify_assessment_results
from datetime import timedelta


async def process_assessment_results(process_id: str, assessment_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process online assessment results and send email notifications.
    
    Args:
        process_id: The hiring process ID
        assessment_results: List of assessment results with candidate_id and score
    
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
        
        for result in assessment_results:
            candidate_id = result["candidate_id"]
            oa_score = result["score"]
            
            # Determine status based on score (threshold: 60)
            new_status = "OA_cleared" if oa_score >= 60 else "OA_rejected"
            
            # Update application in database
            update_result = await applications.update_one(
                {
                    "candidate_id": candidate_id,
                    "process_id": process_id
                },
                {
                    "$set": {
                        "oa_score": oa_score,
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
                        "oa_score": oa_score,
                        "status": new_status
                    })
        
        # Send email notifications
        process_name = process_data.get("process_name", "Unknown Position")
        email_results = await notify_assessment_results(updated_candidates, process_name)
        
        return {
            "status": "success",
            "total_processed": len(assessment_results),
            "updated_count": update_count,
            "cleared_count": len([c for c in updated_candidates if c["status"] == "OA_cleared"]),
            "rejected_count": len([c for c in updated_candidates if c["status"] == "OA_rejected"]),
            "email_notifications": {
                "sent": email_results["sent"],
                "failed": email_results["failed"],
                "details": email_results["details"]
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to process assessment results: {str(e)}"
        }


async def bulk_update_assessment_scores(process_id: str, score_threshold: int = 60) -> Dict[str, Any]:
    """
    Bulk update assessment scores for all candidates who took the assessment.
    This is a utility function for testing or batch processing.
    """
    try:
        # Get all applications for this process with Resume_shortlisted status
        applications = await db_manager.get_collection("applications")
        shortlisted_apps = []
        
        async for app in applications.find({
            "process_id": process_id,
            "status": "Resume_shortlisted"
        }):
            shortlisted_apps.append(app)
        
        if not shortlisted_apps:
            return {"message": "No shortlisted candidates found for assessment"}
        
        # Simulate assessment results (in real scenario, this would come from assessment system)
        import random
        assessment_results = []
        
        for app in shortlisted_apps:
            # Generate random score for simulation
            score = random.randint(30, 95)
            assessment_results.append({
                "candidate_id": app["candidate_id"],
                "score": score
            })
        
        # Process the results
        return await process_assessment_results(process_id, assessment_results)
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to bulk update assessment scores: {str(e)}"
        }


async def process_oa_deadline(process_id: str) -> Dict[str, Any]:
    """Process OA deadline - evaluate OA results and send interview notifications."""
    try:
        # Get process data
        processes = await db_manager.get_collection("Processes")
        process_data = await processes.find_one({"_id": ObjectId(process_id)})
        
        if not process_data:
            return {"error": "Process not found"}
        
        # Get candidates who took OA
        applications = await db_manager.get_collection("applications")
        candidates = await db_manager.get_collection("candidate")
        
        oa_cleared_candidates = []
        oa_rejected_candidates = []
        
        async for app in applications.find({
            "process_id": process_id,
            "oa_score": {"$exists": True}
        }):
            candidate = await candidates.find_one({"_id": ObjectId(app["candidate_id"])})
            if candidate:
                candidate_data = {
                    "_id": app["candidate_id"],
                    "name": candidate.get("name"),
                    "email": candidate.get("email"),
                    "oa_score": app.get("oa_score"),
                    "status": "OA_cleared" if app.get("oa_score", 0) >= 60 else "OA_rejected"
                }
                
                if candidate_data["status"] == "OA_cleared":
                    oa_cleared_candidates.append(candidate_data)
                else:
                    oa_rejected_candidates.append(candidate_data)
        
        # Update statuses in database
        for candidate in oa_cleared_candidates + oa_rejected_candidates:
            await applications.update_one(
                {"candidate_id": candidate["_id"], "process_id": process_id},
                {"$set": {"status": candidate["status"], "updated_at": datetime.now(timezone.utc)}}
            )
        
        # Send interview notifications to cleared candidates
        interview_date = process_data.get("offline_interview_date")
        if interview_date and oa_cleared_candidates:
            interview_date_str = interview_date.strftime("%Y-%m-%d") if hasattr(interview_date, 'strftime') else str(interview_date)
            interview_time = "10:00 AM"
            company_address = "Company Office, Please contact HR for exact address"
            
            from workflow.email_notifications.email_service import send_interview_notifications
            email_results = await send_interview_notifications(
                oa_cleared_candidates,
                process_data.get("process_name", "Unknown Position"),
                interview_date_str,
                interview_time,
                company_address
            )
        else:
            email_results = {"sent": 0, "failed": 0, "details": []}
        
        # Send rejection emails
        if oa_rejected_candidates:
            rejection_results = await notify_assessment_results(oa_rejected_candidates, process_data.get("process_name", "Unknown Position"))
            email_results["sent"] += rejection_results["sent"]
            email_results["failed"] += rejection_results["failed"]
            email_results["details"].extend(rejection_results["details"])
        

        
        return {
            "status": "success",
            "total_candidates": len(oa_cleared_candidates + oa_rejected_candidates),
            "cleared_count": len(oa_cleared_candidates),
            "rejected_count": len(oa_rejected_candidates),
            "emails_sent": email_results["sent"],
            "emails_failed": email_results["failed"],
            "email_details": email_results["details"]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to process OA deadline: {str(e)}"
        }