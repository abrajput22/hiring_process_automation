"""
LangGraph workflow for resume scoring and candidate shortlisting.
This workflow handles the complete process of evaluating resumes against job descriptions
and updating candidate statuses for final selection.
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from db_manager import db_manager
from bson import ObjectId
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from workflow.email_notifications.email_service import notify_resume_results
load_dotenv()

class HiringState(TypedDict):
    """State schema for the hiring workflow."""
    process_id: str
    process_data: Optional[Dict[str, Any]]
    candidates: List[Dict[str, Any]]
    scored_candidates: List[Dict[str, Any]]
    shortlisted_candidates: List[Dict[str, Any]]
    current_node: str
    error_message: Optional[str]
    results: Dict[str, Any]


def get_openai_client() -> ChatOpenAI:
    llm = ChatOpenAI(
        model="gemini-2.0-flash", 
        api_key=os.getenv('GEMINI_API_KEY'),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    return llm


async def check_deadline_and_load_candidates(state: HiringState) -> HiringState:
    """
    Node 1: Check if resume deadline has expired and load all candidate states.
    This node triggers when a process's resume uploading deadline expires.
    """
    try:
        process_id = state["process_id"]
        
        # Get process data
        processes = await db_manager.get_collection("Processes")
        try:
            proc = await processes.find_one({"_id": ObjectId(process_id)})
        except Exception:
            return {
                **state,
                "error_message": "Invalid process id",
                "current_node": "error"
            }
        
        if not proc:
            return {
                **state,
                "error_message": "Process not found",
                "current_node": "error"
            }
        
        # Allow shortlisting regardless of deadline status
        
        # Load all applications for this process
        applications = await db_manager.get_collection("applications")
        candidates = await db_manager.get_collection("candidate")
        candidate_list = []
        
        async for app in applications.find({"process_id": process_id}):
            # Get candidate details
            try:
                cand = await candidates.find_one({"_id": ObjectId(app["candidate_id"])})
                if cand:
                    candidate_list.append({
                        "_id": str(cand["_id"]),
                        "name": cand.get("name"),
                        "email": cand.get("email"),
                        "resume_text": app.get("resume_text", ""),  # Resume text from application
                        "status": app.get("status", "Applied"),
                        "resume_match_score": app.get("resume_match_score")
                    })
            except Exception:
                continue
        
        return {
            **state,
            "process_data": proc,
            "candidates": candidate_list,
            "current_node": "score_resumes",
            "error_message": None
        }
        
    except Exception as e:
        return {
            **state,
            "error_message": f"Error in deadline check: {str(e)}",
            "current_node": "error"
        }

async def score_resumes(state: HiringState) -> HiringState:
    """
    Score all candidate resumes against the job description using API call.
    """
    try:
        process_data = state["process_data"]
        candidates = state["candidates"]
        
        if not process_data or not candidates:
            return {
                **state,
                "error_message": "Missing process data or candidates",
                "current_node": "error"
            }
        
        jd_text = process_data.get("job_description", "")
        if not jd_text:
            return {
                **state,
                "error_message": "Process job description is empty",
                "current_node": "error"
            }
        
        # Score each candidate's resume
        scored_candidates = []
        llm = get_openai_client()
        
        for candidate in candidates:
            resume_text = candidate.get("resume_text", "")
            if not resume_text:
                # Candidates without resume get rejected
                scored_candidate = {
                    **candidate,
                    "resume_match_score": 0,
                    "status": "Resume_rejected"
                }
            else:
                # Call API for resume scoring
                score = await _score_resume_against_jd_api(llm, jd_text, resume_text)
                new_status = "Resume_shortlisted" if score >= 50 else "Resume_rejected"
                scored_candidate = {
                    **candidate,
                    "resume_match_score": score,
                    "status": new_status
                }
            
            scored_candidates.append(scored_candidate)
        
        return {
            **state,
            "scored_candidates": scored_candidates,
            "current_node": "update_database",
            "error_message": None
        }
        
    except Exception as e:
        return {
            **state,
            "error_message": f"Error in resume scoring: {str(e)}",
            "current_node": "error"
        }


async def update_database(state: HiringState) -> HiringState:
    """
    Update candidate states in the database with scores and new statuses.
    """
    try:
        scored_candidates = state["scored_candidates"]
        process_id = state["process_id"]
        
        if not scored_candidates:
            return {
                **state,
                "error_message": "No scored candidates to update",
                "current_node": "error"
            }
        
        # Update applications in database
        applications = await db_manager.get_collection("applications")
        updated_count = 0
        shortlisted_count = 0
        failed_updates = []
        
        for candidate in scored_candidates:
            try:
                await applications.update_one(
                    {
                        "candidate_id": candidate["_id"],
                        "process_id": process_id
                    },
                    {
                        "$set": {
                            "resume_match_score": candidate["resume_match_score"],
                            "status": candidate["status"],
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                updated_count += 1
                
                if candidate["resume_match_score"] >= 50:
                    shortlisted_count += 1
                    
            except Exception as e:
                print(f"Failed to update candidate {candidate['_id']}: {e}")
                failed_updates.append({
                    "candidate_id": candidate['_id'],
                    "error": str(e),
                    "score": candidate['resume_match_score'],
                    "status": candidate['status']
                })
        
        # Select shortlisted and rejected candidates
        shortlisted_candidates = [
            c for c in scored_candidates if c["resume_match_score"] >= 50
        ]
        rejected_candidates = [
            c for c in scored_candidates if c["resume_match_score"] < 50
        ]
        
        # Calculate actual counts from scored data
        actual_shortlisted = len(shortlisted_candidates)
        actual_rejected = len(rejected_candidates)
        
        return {
            **state,
            "shortlisted_candidates": shortlisted_candidates,
            "current_node": "send_emails",
            "results": {
                "total_candidates": len(scored_candidates),
                "updated_candidates": updated_count,
                "failed_updates": len(failed_updates),
                "shortlisted_candidates": actual_shortlisted,
                "rejected_candidates": actual_rejected,
                "shortlist_percentage": (actual_shortlisted / len(scored_candidates)) * 100 if scored_candidates else 0,
                "db_update_success_rate": (updated_count / len(scored_candidates)) * 100 if scored_candidates else 0,
                "failed_update_details": failed_updates
            },
            "error_message": None
        }
        
    except Exception as e:
        return {
            **state,
            "error_message": f"Error updating database: {str(e)}",
            "current_node": "error"
        }


async def send_email_notifications(state: HiringState) -> HiringState:
    """
    Send email notifications to candidates about resume shortlisting results.
    """
    try:
        scored_candidates = state["scored_candidates"]
        process_data = state["process_data"]
        
        if not scored_candidates or not process_data:
            return {
                **state,
                "error_message": "Missing candidates or process data for email notifications",
                "current_node": "error"
            }
        
        process_name = process_data.get("process_name", "Unknown Position")
        
        # Send email notifications with OA links
        email_results = await notify_resume_results(scored_candidates, process_name, process_data)
        

        
        # Update results with email information
        updated_results = {
            **state["results"],
            "email_notifications": {
                "emails_sent": email_results["sent"],
                "emails_failed": email_results["failed"],
                "email_details": email_results["details"]
            }
        }
        
        return {
            **state,
            "current_node": "complete",
            "results": updated_results,
            "error_message": None
        }
        
    except Exception as e:
        return {
            **state,
            "error_message": f"Error sending email notifications: {str(e)}",
            "current_node": "error"
        }


async def handle_error(state: HiringState) -> HiringState:
    """Handle errors in the workflow."""
    return {
        **state,
        "current_node": "error",
        "results": {
            "error": state.get("error_message", "Unknown error occurred")
        }
    }


async def _score_resume_against_jd_api(llm: ChatOpenAI, jd_text: str, resume_text: str) -> int:
    """
    Score resume against job description using ChatOpenAI.
    Returns integer score from 0-100.
    """
    prompt = (
        "You are a strict evaluator. Compare the candidate's resume to the job description. "
        "Return ONLY an integer from 0 to 100 indicating match score; no text, no percent sign.\n\n"
        f"Job Description:\n{jd_text}\n\nResume:\n{resume_text}\n\nScore:"
    )
    
    try:
        # Use ChatOpenAI invoke method
        response = await llm.ainvoke(prompt)
        text = response.content.strip()
        
        # Extract numeric score
        digits = ''.join(ch for ch in text if ch.isdigit())
        score = int(digits) if digits else 0
        return max(0, min(100, score))
        
    except Exception as e:
        print(f"Error scoring resume: {e}")
        return 0


def create_hiring_workflow() -> StateGraph:
    """
    Create and configure the LangGraph workflow for hiring process.
    """
    workflow = StateGraph(HiringState)
    
    # Add nodes
    workflow.add_node("check_deadline", check_deadline_and_load_candidates)
    workflow.add_node("score_resumes", score_resumes)
    workflow.add_node("update_database", update_database)
    workflow.add_node("send_emails", send_email_notifications)
    workflow.add_node("error", handle_error)
    
    # Define the flow
    workflow.set_entry_point("check_deadline")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "check_deadline",
        lambda state: state["current_node"],
        {
            "score_resumes": "score_resumes",
            "error": "error"
        }
    )
    
    workflow.add_conditional_edges(
        "score_resumes",
        lambda state: state["current_node"],
        {
            "update_database": "update_database",
            "error": "error"
        }
    )
    
    workflow.add_conditional_edges(
        "update_database",
        lambda state: state["current_node"],
        {
            "send_emails": "send_emails",
            "error": "error"
        }
    )
    
    workflow.add_conditional_edges(
        "send_emails",
        lambda state: state["current_node"],
        {
            "complete": END,
            "error": "error"
        }
    )
    
    workflow.add_edge("error", END)
    
    return workflow


async def run_resume_scoring_workflow(process_id: str) -> Dict[str, Any]:
    """
    Run the resume scoring workflow for a specific process.
    This is the main entry point for the workflow.
    """
    workflow = create_hiring_workflow()
    app = workflow.compile()
    
    initial_state = HiringState(
        process_id=process_id,
        process_data=None,
        candidates=[],
        scored_candidates=[],
        shortlisted_candidates=[],
        current_node="check_deadline",
        error_message=None,
        results={}
    )
    
    try:
        result = await app.ainvoke(initial_state)
        return result
    except Exception as e:
        return {
            "error": f"Workflow execution failed: {str(e)}",
            "process_id": process_id
        }


# Example usage and testing
if __name__ == "__main__":
    async def test_workflow():
        """Test the workflow with a sample process ID."""
        process_id = "your_process_id_here"
        result = await run_resume_scoring_workflow(process_id)
        print("Workflow result:", result)
    
    # Run test
    asyncio.run(test_workflow())