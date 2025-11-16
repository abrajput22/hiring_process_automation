"""
Email Service Integration for Hiring Workflows.
Provides functions to trigger emails based on workflow events.
"""

from typing import Dict, Any, List
from .email_workflow import (
    send_resume_shortlisted_email,
    send_online_assessment_cleared_email,
    send_offline_interview_cleared_email,
    send_rejection_email,
    send_interview_notification_email
)


async def notify_resume_results(candidates: List[Dict[str, Any]], process_name: str, process_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Send email notifications for resume shortlisting results."""
    results = {"sent": 0, "failed": 0, "details": []}
    
    for candidate in candidates:
        try:
            if candidate["status"] == "Resume_shortlisted":
                # Generate OA links for both localhost and Render
                oa_date = process_data.get("assessment_date") if process_data else "TBD"
                if isinstance(oa_date, str):
                    oa_date_str = oa_date
                else:
                    oa_date_str = oa_date.strftime("%Y-%m-%d %H:%M IST") if oa_date else "TBD"
                
                process_id = process_data.get('_id', 'process_id') if process_data else 'process_id'
                candidate_id = candidate['_id']
                
                localhost_link = f"http://localhost:8000/{candidate_id}/OA/{process_id}"
                render_link = f"https://hiring-process-automation.onrender.com/{candidate_id}/OA/{process_id}"
                
                result = await send_resume_shortlisted_email(
                    candidate["email"],
                    candidate["name"],
                    process_name,
                    candidate["resume_match_score"],
                    localhost_link,
                    render_link,
                    oa_date_str
                )
            else:
                result = await send_rejection_email(
                    candidate["email"],
                    candidate["name"],
                    process_name
                )
            
            if result["status"] == "success":
                results["sent"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "candidate": candidate["name"],
                "email": candidate["email"],
                "status": result["status"],
                "score": candidate["resume_match_score"]
            })
            
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "candidate": candidate.get("name", "Unknown"),
                "email": candidate.get("email", "Unknown"),
                "status": "error",
                "message": str(e)
            })
    
    return results


async def notify_assessment_results(candidates: List[Dict[str, Any]], process_name: str) -> Dict[str, Any]:
    """Send email notifications for online assessment results."""
    results = {"sent": 0, "failed": 0, "details": []}
    
    for candidate in candidates:
        try:
            if candidate["status"] == "OA_cleared":
                result = await send_online_assessment_cleared_email(
                    candidate["email"],
                    candidate["name"],
                    process_name,
                    candidate["oa_score"]
                )
            else:
                result = await send_rejection_email(
                    candidate["email"],
                    candidate["name"],
                    process_name
                )
            
            if result["status"] == "success":
                results["sent"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "candidate": candidate["name"],
                "email": candidate["email"],
                "status": result["status"],
                "score": candidate["oa_score"]
            })
            
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "candidate": candidate.get("name", "Unknown"),
                "email": candidate.get("email", "Unknown"),
                "status": "error",
                "message": str(e)
            })
    
    return results


async def notify_interview_results(candidates: List[Dict[str, Any]], process_name: str) -> Dict[str, Any]:
    """Send email notifications for offline interview results."""
    results = {"sent": 0, "failed": 0, "details": []}
    
    for candidate in candidates:
        try:
            if candidate["status"] == "Interview_cleared":
                result = await send_offline_interview_cleared_email(
                    candidate["email"],
                    candidate["name"],
                    process_name
                )
            else:
                result = await send_rejection_email(
                    candidate["email"],
                    candidate["name"],
                    process_name
                )
            
            if result["status"] == "success":
                results["sent"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "candidate": candidate["name"],
                "email": candidate["email"],
                "status": result["status"]
            })
            
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "candidate": candidate.get("name", "Unknown"),
                "email": candidate.get("email", "Unknown"),
                "status": "error",
                "message": str(e)
            })
    
    return results


async def send_interview_notifications(candidates: List[Dict[str, Any]], process_name: str, 
                                     interview_date: str, interview_time: str, company_address: str) -> Dict[str, Any]:
    """Send interview notification emails to OA cleared candidates."""
    results = {"sent": 0, "failed": 0, "details": []}
    
    for candidate in candidates:
        try:
            result = await send_interview_notification_email(
                candidate["email"],
                candidate["name"],
                process_name,
                interview_date,
                interview_time,
                company_address
            )
            
            if result["status"] == "success":
                results["sent"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "candidate": candidate["name"],
                "email": candidate["email"],
                "status": result["status"],
                "message": result["message"]
            })
            
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "candidate": candidate.get("name", "Unknown"),
                "email": candidate.get("email", "Unknown"),
                "status": "error",
                "message": f"Failed to send email: {str(e)}"
            })
    
    return results


async def send_selection_notifications(selected_candidates: List[Dict[str, Any]], 
                                     rejected_candidates: List[Dict[str, Any]], 
                                     process_name: str, package_offered: str) -> Dict[str, Any]:
    """Send final selection and rejection emails."""
    results = {"sent": 0, "failed": 0, "details": []}
    
    # Send selection emails
    for candidate in selected_candidates:
        try:
            result = await send_selection_email(
                candidate["email"],
                candidate["name"],
                process_name,
                package_offered
            )
            
            if result["status"] == "success":
                results["sent"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "candidate": candidate["name"],
                "email": candidate["email"],
                "status": result["status"],
                "type": "selection"
            })
            
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "candidate": candidate.get("name", "Unknown"),
                "email": candidate.get("email", "Unknown"),
                "status": "error",
                "type": "selection",
                "message": str(e)
            })
    
    # Send rejection emails
    for candidate in rejected_candidates:
        try:
            result = await send_rejection_email(
                candidate["email"],
                candidate["name"],
                process_name
            )
            
            if result["status"] == "success":
                results["sent"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "candidate": candidate["name"],
                "email": candidate["email"],
                "status": result["status"],
                "type": "rejection"
            })
            
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "candidate": candidate.get("name", "Unknown"),
                "email": candidate.get("email", "Unknown"),
                "status": "error",
                "type": "rejection",
                "message": str(e)
            })
    
    return results


async def send_selection_email(email: str, name: str, process_name: str, package_offered: str) -> Dict[str, Any]:
    """Send selection confirmation email."""
    try:
        from .email_workflow import send_final_selection_email
        return await send_final_selection_email(email, name, process_name, package_offered)
    except Exception as e:
        return {"status": "error", "message": f"Failed to send selection email: {str(e)}"}