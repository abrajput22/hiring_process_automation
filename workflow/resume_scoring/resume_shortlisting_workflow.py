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
        print(f"📋 T6: STAGE 1 Loading candidates at {datetime.now()}")
        
        # Get process data
        processes = await db_manager.get_collection("Processes")
        try:
            proc = await processes.find_one({"_id": ObjectId(process_id)})
        except Exception:
            print(f"❌ STAGE 1 ERROR: Invalid process ID {process_id}")
            return {
                **state,
                "error_message": "Invalid process id",
                "current_node": "error"
            }
        
        if not proc:
            print(f"❌ STAGE 1 ERROR: Process {process_id} not found")
            return {
                **state,
                "error_message": "Process not found",
                "current_node": "error"
            }
        
        print(f"✅ STAGE 1: Process found - {proc.get('process_name', 'Unknown')}")
        
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
        
        print(f"✅ T7: STAGE 1 COMPLETE at {datetime.now()} - Loaded {len(candidate_list)} candidates")
        return {
            **state,
            "process_data": proc,
            "candidates": candidate_list,
            "current_node": "score_resumes",
            "error_message": None
        }
        
    except Exception as e:
        print(f"❌ STAGE 1 ERROR: {str(e)}")
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
        print(f"🤖 T8: STAGE 2 AI Scoring START at {datetime.now()} - {len(candidates)} candidates")
        
        if not process_data or not candidates:
            print(f"❌ STAGE 2 ERROR: Missing process data or candidates")
            return {
                **state,
                "error_message": "Missing process data or candidates",
                "current_node": "error"
            }
        
        jd_text = process_data.get("job_description", "")
        if not jd_text:
            print(f"❌ STAGE 2 ERROR: Job description is empty")
            return {
                **state,
                "error_message": "Process job description is empty",
                "current_node": "error"
            }
        
        # Score each candidate's resume
        scored_candidates = []
        llm = None
        try:
            llm = get_openai_client()
            print(f"✅ STAGE 2: AI client initialized")
        except Exception as e:
            print(f"⚠️ STAGE 2: AI client failed, using fallback - {str(e)}")
            llm = None
        
        for i, candidate in enumerate(candidates):
            print(f"🔍 STAGE 2: Scoring candidate {i+1}/{len(candidates)} - {candidate.get('email', 'Unknown')}")
            resume_text = candidate.get("resume_text", "")
            if not resume_text:
                scored_candidate = {
                    **candidate,
                    "resume_match_score": 0,
                    "status": "Resume_rejected"
                }
            elif llm is None:
                # Fallback: shortlist candidates with resumes
                scored_candidate = {
                    **candidate,
                    "resume_match_score": 75,
                    "status": "Resume_shortlisted"
                }
            else:
                score = await _score_resume_against_jd_api(llm, jd_text, resume_text)
                new_status = "Resume_shortlisted" if score >= 50 else "Resume_rejected"
                scored_candidate = {
                    **candidate,
                    "resume_match_score": score,
                    "status": new_status
                }
            
            scored_candidates.append(scored_candidate)
        
        print(f"✅ T9: STAGE 2 COMPLETE at {datetime.now()} - {len(scored_candidates)} candidates scored")
        return {
            **state,
            "scored_candidates": scored_candidates,
            "current_node": "update_database",
            "error_message": None
        }
        
    except Exception as e:
        print(f"❌ STAGE 2 ERROR: AI scoring failed - {str(e)}")
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
        print(f"💾 T10: STAGE 3 DB Update START at {datetime.now()} - {len(scored_candidates)} candidates")
        
        if not scored_candidates:
            print(f"❌ STAGE 3 ERROR: No scored candidates to update")
            return {
                **state,
                "error_message": "No scored candidates to update",
                "current_node": "error"
            }
        
        # Update applications in database
        applications = await db_manager.get_collection("applications")
        updated_count = 0
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
            except Exception as e:
                failed_updates.append({
                    "candidate_id": candidate['_id'],
                    "error": str(e)
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
        
        print(f"✅ T11: STAGE 3 COMPLETE at {datetime.now()} - Updated: {updated_count}/{len(scored_candidates)}")
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
        print(f"❌ STAGE 3 ERROR: Database update failed - {str(e)}")
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
        print(f"📧 T12: STAGE 4 Email START at {datetime.now()}")
        
        if not scored_candidates or not process_data:
            print(f"❌ STAGE 4 ERROR: Missing candidates or process data")
            return {
                **state,
                "error_message": "Missing candidates or process data for email notifications",
                "current_node": "error"
            }
        
        process_name = process_data.get("process_name", "Unknown Position")
        shortlisted = [c for c in scored_candidates if c["resume_match_score"] >= 50]
        rejected = [c for c in scored_candidates if c["resume_match_score"] < 50]
        
        print(f"📧 STAGE 4: Sending emails - {len(shortlisted)} shortlisted, {len(rejected)} rejected")
        
        # Send email notifications with OA links
        email_results = await notify_resume_results(scored_candidates, process_name, process_data)
        
        print(f"✅ T13: STAGE 4 COMPLETE at {datetime.now()} - Emails: {email_results['sent']} sent, {email_results['failed']} failed")
        
        # Log email details
        for detail in email_results.get('details', []):
            if detail.get('status') == 'success':
                print(f"📧 EMAIL SENT: {detail.get('email')} - Resume Shortlisting Result")
            else:
                print(f"❌ EMAIL FAILED: {detail.get('email')} - {detail.get('message', 'Unknown error')}")
        
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
        print(f"❌ STAGE 4 ERROR: Email notifications failed - {str(e)}")
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
    prompt = f"Score this resume (0-100) for job match. Return only number:\n\nJob: {jd_text[:500]}\n\nResume: {resume_text[:1000]}\n\nScore:"
    
    try:
        print(f"🤖 T_AI_START: Calling Gemini API at {datetime.now()}")
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=3.0)
        text = response.content.strip()
        print(f"🤖 T_AI_END: Gemini response at {datetime.now()}: {text}")
        
        digits = ''.join(ch for ch in text if ch.isdigit())
        score = int(digits) if digits else 75
        final_score = max(0, min(100, score))
        print(f"🤖 FINAL SCORE: {final_score}")
        return final_score
        
    except asyncio.TimeoutError:
        print(f"⏰ AI TIMEOUT: Using fallback score 75")
        return 75
    except Exception as e:
        print(f"❌ AI ERROR: {e} - Using fallback score 75")
        return 75


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


async def run_resume_scoring_workflow(process_id: str, trigger_type: str = "MANUAL") -> Dict[str, Any]:
    """
    Run the resume scoring workflow for a specific process.
    This is the main entry point for the workflow.
    """
    from datetime import datetime
    print(f"🚀 T1: WORKFLOW START at {datetime.now()} - Process: {process_id}")
    
    try:
        print(f"🔧 T2: Creating workflow at {datetime.now()}")
        workflow = create_hiring_workflow()
        app = workflow.compile()
        print(f"✅ T3: Workflow compiled at {datetime.now()}")
        
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
        
        print(f"⏳ T4: Starting execution at {datetime.now()}")
        result = await app.ainvoke(initial_state)
        print(f"🎉 T5: WORKFLOW COMPLETE at {datetime.now()}")
        return result
        
    except Exception as e:
        print(f"❌ WORKFLOW ERROR at {datetime.now()}: {str(e)}")
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