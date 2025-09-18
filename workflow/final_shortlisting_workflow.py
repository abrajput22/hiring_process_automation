"""
Final Shortlisting Workflow.
Handles final candidate selection based on combined scores and sends selection emails.
"""

from typing import Dict, List, Any
from datetime import datetime, timezone
from db_manager import db_manager
from bson import ObjectId
from workflow.email_notifications.email_service import send_selection_notifications


async def process_final_shortlisting(process_id: str) -> Dict[str, Any]:
    """
    Process final shortlisting based on combined scores.
    This runs automatically on the interview deadline.
    """
    try:
        processes = await db_manager.get_collection("Processes")
        candidates = await db_manager.get_collection("candidate")
        applications = await db_manager.get_collection("applications")
        
        # Get process data
        process_data = await processes.find_one({"_id": ObjectId(process_id)})
        if not process_data:
            return {"error": "Process not found"}
        
        # Get OA cleared candidates with all scores
        selected_candidates = []
        rejected_candidates = []
        
        async for app in applications.find({
            "process_id": process_id,
            "status": "OA_cleared",
            "hr_score": {"$exists": True}
        }):
            oa_score = app.get("oa_score", 0)
            tech_score = app.get("tech_score", 0)
            hr_score = app.get("hr_score", 0)
            
            # Calculate weighted combined score
            combined_score = (oa_score * 0.4) + (tech_score * 0.3) + (hr_score * 0.3)
            
            # Final selection threshold: 70
            new_status = "Final_selected" if combined_score >= 70 else "Final_rejected"
            
            # Update application status
            await applications.update_one(
                {"_id": app["_id"]},
                {"$set": {
                    "status": new_status,
                    "final_score": combined_score,
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            # Get candidate details
            candidate = await candidates.find_one({"_id": ObjectId(app["candidate_id"])})
            if candidate:
                candidate_data = {
                    "_id": app["candidate_id"],
                    "name": candidate.get("name"),
                    "email": candidate.get("email"),
                    "combined_score": combined_score,
                    "status": new_status
                }
                
                if new_status == "Final_selected":
                    selected_candidates.append(candidate_data)
                else:
                    rejected_candidates.append(candidate_data)
        
        # Send email notifications
        process_name = process_data.get("process_name", "Unknown Position")
        package_offered = process_data.get("package_offered", "Competitive package")
        
        email_results = await send_selection_notifications(
            selected_candidates,
            rejected_candidates,
            process_name,
            package_offered
        )
        
        return {
            "status": "success",
            "total_processed": len(selected_candidates) + len(rejected_candidates),
            "selected_count": len(selected_candidates),
            "rejected_count": len(rejected_candidates),
            "emails_sent": email_results["sent"],
            "emails_failed": email_results["failed"],
            "email_details": email_results["details"]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to process final shortlisting: {str(e)}"
        }


async def process_interview_deadline(process_id: str) -> Dict[str, Any]:
    """Process interview deadline - trigger final shortlisting."""
    try:
        # Check if HR has provided scores for OA cleared candidates
        applications = await db_manager.get_collection("applications")
        
        # Count OA cleared candidates
        oa_cleared_count = await applications.count_documents({
            "process_id": process_id,
            "status": "OA_cleared"
        })
        
        # Count those with HR scores
        scored_count = await applications.count_documents({
            "process_id": process_id,
            "status": "OA_cleared",
            "hr_score": {"$exists": True}
        })
        
        if oa_cleared_count == 0:
            return {
                "status": "info",
                "message": "No OA cleared candidates found for final shortlisting"
            }
        
        if scored_count < oa_cleared_count:
            return {
                "status": "warning",
                "message": f"Only {scored_count} out of {oa_cleared_count} candidates have HR scores. Final shortlisting postponed.",
                "oa_cleared_count": oa_cleared_count,
                "scored_count": scored_count
            }
        
        # All candidates have scores, proceed with final shortlisting
        return await process_final_shortlisting(process_id)
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to process interview deadline: {str(e)}"
        }