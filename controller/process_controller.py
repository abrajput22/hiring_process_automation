"""
Controller for hiring process functionality.
Handles all business logic related to hiring processes, shortlisting, and process management.
"""

import os
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException
from db_manager import db_manager
from db_schema import HiringProcess
from bson import ObjectId
from openai import OpenAI
import pymongo.errors





async def create_hiring_process(process: HiringProcess):
    """Create a new hiring process and schedule deadline."""
    for attempt in range(3):
        try:
            processes = await db_manager.get_collection("Processes")
            doc = process.dict()
            

            
            result = await processes.insert_one(doc)
            process_id = str(result.inserted_id)
            
            # Auto-schedule jobs for this process
            try:
                from workflow.resume_scoring.ap_scheduler_trigger_on_deadline import schedule_process
                doc["_id"] = result.inserted_id
                await schedule_process(doc)
                print(f"Auto-scheduled jobs for process {process_id}")
            except Exception as e:
                print(f"Failed to auto-schedule jobs: {e}")
            
            return {"process_id": process_id}
        except (pymongo.errors.NetworkTimeout, pymongo.errors.ServerSelectionTimeoutError) as e:
            if attempt == 2:
                raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
            await asyncio.sleep(1)


async def list_hiring_processes(hr_id: Optional[str] = None) -> List[dict]:
    """List all hiring processes, optionally filtered by HR ID."""
    for attempt in range(3):
        try:
            processes = await db_manager.get_collection("Processes")
            query = {"hr_id": hr_id} if hr_id else {}
            cursor = processes.find(query)
            items = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                items.append(doc)
            return items
        except (pymongo.errors.NetworkTimeout, pymongo.errors.ServerSelectionTimeoutError) as e:
            if attempt == 2:
                raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
            await asyncio.sleep(1)


async def shortlist_process_candidates(process_id: str):
    """
    Trigger the LangGraph workflow for resume scoring and shortlisting.
    This endpoint delegates to the workflow instead of doing scoring directly.
    """
    try:
        import pytz
        
        # Check if deadline has passed
        processes = await db_manager.get_collection("Processes")
        proc = await processes.find_one({"_id": ObjectId(process_id)})
        if not proc:
            raise HTTPException(status_code=404, detail="Process not found")
        
        ist_tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist_tz)
        resume_deadline = proc.get("resume_deadline")
        
        if resume_deadline:
            if resume_deadline.tzinfo is None:
                resume_deadline = ist_tz.localize(resume_deadline)
            if now > resume_deadline:
                raise HTTPException(status_code=400, detail="Resume deadline has passed")
        
        # Cancel all scheduled jobs for this process
        try:
            from workflow.resume_scoring.ap_scheduler_trigger_on_deadline import scheduler
            scheduler.remove_job(f"resume_{process_id}")
            scheduler.remove_job(f"oa_{process_id}")
            scheduler.remove_job(f"interview_{process_id}")
        except:
            pass
        
        from workflow.resume_scoring.resume_shortlisting_workflow import run_resume_scoring_workflow
        result = await run_resume_scoring_workflow(process_id)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "message": "Resume scoring workflow completed successfully",
            "results": result.get("results", {}),
            "shortlisted_count": len(result.get("shortlisted_candidates", [])),
            "rejected_count": result.get("results", {}).get("rejected_candidates", 0),
            "total_candidates": result.get("results", {}).get("total_candidates", 0)
        }
        
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=500, detail="Hiring workflow not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


async def sync_application_status(process_id: str):
    """Manually sync application statuses based on scores"""
    try:
        applications = await db_manager.get_collection("applications")
        
        # Find all applications for this process that have scores but wrong status
        cursor = applications.find({"process_id": process_id, "resume_match_score": {"$exists": True}})
        updated_count = 0
        
        async for app in cursor:
            score = app.get("resume_match_score", 0)
            current_status = app.get("status", "Applied")
            
            # Determine correct status based on score
            correct_status = "Resume_shortlisted" if score >= 50 else "Resume_rejected"
            
            # Update if status is wrong
            if current_status != correct_status:
                await applications.update_one(
                    {"_id": app["_id"]},
                    {"$set": {
                        "status": correct_status,
                        "updated_at": datetime.now()
                    }}
                )
                updated_count += 1
        
        return {
            "message": "Status sync completed",
            "updated_count": updated_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


async def delete_hiring_process(process_id: str):
    """Delete a hiring process and all related applications."""
    try:
        processes = await db_manager.get_collection("Processes")
        applications = await db_manager.get_collection("applications")
        
        # Delete all applications for this process
        await applications.delete_many({"process_id": process_id})
        
        # Delete the process
        result = await processes.delete_one({"_id": ObjectId(process_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Process not found")
        
        # Unschedule from APScheduler
        try:
            from workflow.resume_scoring.ap_scheduler_trigger_on_deadline import unschedule_process
            unschedule_process(process_id)
        except Exception as e:
            print(f"Failed to unschedule process: {e}")
        
        return {"message": "Process deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


async def get_process_detail(process_id: str) -> dict:
    """Get detailed information about a specific hiring process including candidate statuses."""
    processes = await db_manager.get_collection("Processes")
    candidates = await db_manager.get_collection("candidate")
    applications = await db_manager.get_collection("applications")
    
    try:
        proc = await processes.find_one({"_id": ObjectId(process_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid process id")
    
    if not proc:
        raise HTTPException(status_code=404, detail="Process not found")
    
    proc["_id"] = str(proc["_id"])
    


    # Categorize candidates by status from applications
    application = []
    shortlisted = []
    oa_shortlisted = []
    oa_rejected = []
    final_shortlisted = []

    async for app in applications.find({"process_id": process_id}):
        # Get candidate details
        try:
            cand = await candidates.find_one({"_id": ObjectId(app["candidate_id"])})
            if not cand:
                print(f"Candidate not found for ID: {app['candidate_id']}")
                continue
                
            # Only show OA score if status has been processed (OA_cleared/OA_rejected/Final_selected/Final_rejected)
            show_oa_score = app.get("status") in ["OA_cleared", "OA_rejected", "Final_selected", "Final_rejected"]
            
            row = {
                "name": cand.get("name"), 
                "email": cand.get("email"), 
                "status": app.get("status"),
                "resume_match_score": app.get("resume_match_score"),
                "oa_score": app.get("oa_score") if show_oa_score else None,
                "tech_score": app.get("tech_score"),
                "hr_score": app.get("hr_score")
            }
            status = app.get("status", "Applied")
            print(f"Processing candidate: {cand.get('email')} with status: {status}")
            
            if status == "Applied":
                application.append(row)
            elif status == "Resume_shortlisted":
                shortlisted.append(row)
            elif status == "Resume_rejected":
                # Don't show resume rejected
                pass
            elif status == "OA_cleared":
                oa_shortlisted.append(row)
            elif status == "OA_rejected":
                oa_rejected.append(row)
            elif status == "Final_selected":
                final_shortlisted.append(row)
            elif status == "Final_rejected":
                # Don't show final rejected
                pass
            else:
                # Any other status goes to applications
                application.append(row)
        except Exception as e:
            print(f"Error processing application: {e}")
            continue

    print(f"Final counts - Applications: {len(application)}, Shortlisted: {len(shortlisted)}, OA Shortlisted: {len(oa_shortlisted)}, Final: {len(final_shortlisted)}")
    
    return {
        "process": proc,
        "application": application,
        "shortlisted": shortlisted,
        "oa_shortlisted": oa_shortlisted,
        "oa_rejected": oa_rejected,
        "final_shortlisted": final_shortlisted,
    }


async def get_oa_shortlisted_candidates(process_id: str) -> dict:
    """Get OA shortlisted candidates for HR scoring."""
    try:
        processes = await db_manager.get_collection("Processes")
        candidates = await db_manager.get_collection("candidate")
        applications = await db_manager.get_collection("applications")
        
        # Get process details
        proc = await processes.find_one({"_id": ObjectId(process_id)})
        if not proc:
            raise HTTPException(status_code=404, detail="Process not found")
        
        proc["_id"] = str(proc["_id"])
        
        # Get OA cleared candidates
        oa_candidates = []
        async for app in applications.find({"process_id": process_id, "status": "OA_cleared"}):
            cand = await candidates.find_one({"_id": ObjectId(app["candidate_id"])})
            if cand:
                oa_candidates.append({
                    "candidate_id": app["candidate_id"],
                    "name": cand.get("name"),
                    "email": cand.get("email"),
                    "oa_score": app.get("oa_score"),
                    "tech_score": app.get("tech_score"),
                    "hr_score": app.get("hr_score"),
                    "status": app.get("status")
                })
        
        return {
            "process": proc,
            "candidates": oa_candidates
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get OA shortlisted candidates: {str(e)}")


async def save_hr_scores(process_id: str, scores: List[dict]) -> dict:
    """Save technical and HR scores for candidates."""
    try:
        applications = await db_manager.get_collection("applications")
        updated_count = 0
        
        for score_data in scores:
            candidate_id = score_data["candidate_id"]
            tech_score = score_data.get("tech_score", 0)
            hr_score = score_data.get("hr_score", 0)
            
            result = await applications.update_one(
                {"candidate_id": candidate_id, "process_id": process_id},
                {"$set": {"tech_score": tech_score, "hr_score": hr_score, "updated_at": datetime.now()}}
            )
            
            if result.modified_count > 0:
                updated_count += 1
        
        return {"updated_count": updated_count}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save scores: {str(e)}")


async def execute_final_shortlisting(process_id: str) -> dict:
    """Execute final shortlisting based on combined scores and send selection emails."""
    try:
        processes = await db_manager.get_collection("Processes")
        candidates = await db_manager.get_collection("candidate")
        applications = await db_manager.get_collection("applications")
        
        # Get process details
        proc = await processes.find_one({"_id": ObjectId(process_id)})
        if not proc:
            raise HTTPException(status_code=404, detail="Process not found")
        
        # Get OA cleared candidates with scores
        selected_candidates = []
        rejected_candidates = []
        
        async for app in applications.find({"process_id": process_id, "status": "OA_cleared"}):
            oa_score = app.get("oa_score", 0)
            tech_score = app.get("tech_score", 0)
            hr_score = app.get("hr_score", 0)
            
            # Calculate combined score (weighted average)
            combined_score = (oa_score * 0.4) + (tech_score * 0.3) + (hr_score * 0.3)
            
            # Final selection threshold: 70
            new_status = "Final_selected" if combined_score >= 70 else "Final_rejected"
            
            # Update status
            await applications.update_one(
                {"_id": app["_id"]},
                {"$set": {"status": new_status, "updated_at": datetime.now()}}
            )
            
            # Get candidate details
            cand = await candidates.find_one({"_id": ObjectId(app["candidate_id"])})
            if cand:
                candidate_data = {
                    "_id": app["candidate_id"],
                    "name": cand.get("name"),
                    "email": cand.get("email"),
                    "combined_score": combined_score,
                    "status": new_status
                }
                
                if new_status == "Final_selected":
                    selected_candidates.append(candidate_data)
                else:
                    rejected_candidates.append(candidate_data)
        
        # Send selection emails
        from workflow.email_notifications.email_service import send_selection_notifications, send_hr_summary_email
        email_results = await send_selection_notifications(
            selected_candidates,
            rejected_candidates,
            proc.get("process_name", "Unknown Position"),
            proc.get("package_offered", "Competitive package")
        )
        

        
        return {
            "selected_count": len(selected_candidates),
            "rejected_count": len(rejected_candidates),
            "emails_sent": email_results["sent"],
            "emails_failed": email_results["failed"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute final shortlisting: {str(e)}")


async def trigger_oa_workflow(process_id: str) -> dict:
    """Trigger OA workflow manually."""
    try:
        from workflow.assessment_workflow import process_oa_deadline
        result = await process_oa_deadline(process_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OA workflow failed: {str(e)}")


async def trigger_final_workflow(process_id: str) -> dict:
    """Trigger final shortlisting workflow manually."""
    try:
        from workflow.final_shortlisting_workflow import process_interview_deadline
        result = await process_interview_deadline(process_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Final workflow failed: {str(e)}")

async def trigger_oa_workflow(process_id: str) -> dict:
    """Trigger OA workflow manually."""
    try:
        import pytz
        
        # Check if deadline has passed
        processes = await db_manager.get_collection("Processes")
        proc = await processes.find_one({"_id": ObjectId(process_id)})
        if not proc:
            raise HTTPException(status_code=404, detail="Process not found")
        
        ist_tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist_tz)
        assessment_date = proc.get("assessment_date")
        
        if assessment_date:
            if assessment_date.tzinfo is None:
                assessment_date = ist_tz.localize(assessment_date)
            if now > assessment_date:
                raise HTTPException(status_code=400, detail="Assessment deadline has passed")
        
        # Cancel scheduled job
        try:
            from workflow.resume_scoring.ap_scheduler_trigger_on_deadline import scheduler
            scheduler.remove_job(f"oa_{process_id}")
        except:
            pass
        
        from workflow.assessment_workflow import process_oa_deadline
        result = await process_oa_deadline(process_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OA workflow failed: {str(e)}")


async def trigger_final_workflow(process_id: str) -> dict:
    """Trigger final shortlisting workflow manually."""
    try:
        import pytz
        
        # Check if deadline has passed
        processes = await db_manager.get_collection("Processes")
        proc = await processes.find_one({"_id": ObjectId(process_id)})
        if not proc:
            raise HTTPException(status_code=404, detail="Process not found")
        
        ist_tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist_tz)
        interview_date = proc.get("offline_interview_date")
        
        if interview_date:
            if interview_date.tzinfo is None:
                interview_date = ist_tz.localize(interview_date)
            if now > interview_date:
                raise HTTPException(status_code=400, detail="Interview deadline has passed")
        
        # Cancel scheduled job
        try:
            from workflow.resume_scoring.ap_scheduler_trigger_on_deadline import scheduler
            scheduler.remove_job(f"interview_{process_id}")
        except:
            pass
        
        from workflow.final_shortlisting_workflow import process_interview_deadline
        result = await process_interview_deadline(process_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Final workflow failed: {str(e)}")