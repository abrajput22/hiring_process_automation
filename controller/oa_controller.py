"""
Online Assessment Controller.
Handles OA page display, date validation, and score submission.
"""

# Configuration: Hours before OA deadline when test window opens
OA_WINDOW_HOURS = 24

from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from datetime import datetime, date
from typing import Dict, Any
from db_manager import db_manager
from bson import ObjectId


# Correct answers for the Python quiz
CORRECT_ANSWERS = {
    "q1": "A",  # <class 'list'>
    "q2": "B",  # append()
    "q3": "C",  # dict = {}
    "q4": "B",  # def
    "q5": "B"   # 6
}


async def get_oa_page(candidate_id: str, process_id: str) -> HTMLResponse:
    """
    Display OA page if time is valid and candidate is eligible.
    URL format: /candidate_id/OA/process_id
    """
    try:
        # Get process data to check assessment timing
        processes = await db_manager.get_collection("Processes")
        process_data = await processes.find_one({"_id": ObjectId(process_id)})
        
        if not process_data:
            raise HTTPException(status_code=404, detail="Process not found")
        
        # Check if OA is currently active (assessment_date - OA_WINDOW_HOURS to assessment_date)
        assessment_date = process_data.get("assessment_date")
        if assessment_date:
            from datetime import timedelta
            import pytz
            
            ist_tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist_tz)
            
            if assessment_date.tzinfo is None:
                assessment_date = ist_tz.localize(assessment_date)
            
            oa_start = assessment_date - timedelta(hours=OA_WINDOW_HOURS)
            oa_end = assessment_date
            
            if now < oa_start:
                return HTMLResponse(f"""
                <html><body style="text-align:center; padding:50px; font-family:Arial;">
                    <h2>Online Assessment Not Available</h2>
                    <p>The assessment will be available from: <strong>{oa_start.strftime('%Y-%m-%d %H:%M IST')}</strong></p>
                    <p>Assessment window: {oa_start.strftime('%H:%M')} to {oa_end.strftime('%H:%M IST')}</p>
                </body></html>
                """)
            elif now > oa_end:
                return HTMLResponse(f"""
                <html><body style="text-align:center; padding:50px; font-family:Arial;">
                    <h2>Assessment Expired</h2>
                    <p>The assessment window was: <strong>{oa_start.strftime('%Y-%m-%d %H:%M')} to {oa_end.strftime('%H:%M IST')}</strong></p>
                    <p>Results will be communicated via email.</p>
                </body></html>
                """)
        else:
            return HTMLResponse("""
            <html><body style="text-align:center; padding:50px; font-family:Arial;">
                <h2>Assessment Not Scheduled</h2>
                <p>The assessment date has not been set yet.</p>
                <p>Please contact HR for more information.</p>
            </body></html>
            """)
        
        # Validate candidate and process
        applications = await db_manager.get_collection("applications")
        application = await applications.find_one({
            "candidate_id": candidate_id,
            "process_id": process_id,
            "status": "Resume_shortlisted"
        })
        
        if not application:
            raise HTTPException(status_code=404, detail="Application not found or not eligible for OA")
        
        # Check if already taken
        if application.get("oa_score") is not None:
            return HTMLResponse(f"""
            <html><body style="text-align:center; padding:50px; font-family:Arial;">
                <h2>Assessment Already Completed</h2>
                <p>You have already taken this assessment.</p>
                <p>Your score: <strong>{application.get('oa_score')}/100</strong></p>
            </body></html>
            """)
        
        # Load and return the OA page
        with open("views/online_assessment.html", "r") as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading OA page: {str(e)}")


async def submit_oa_answers(candidate_id: str, process_id: str, answers: Dict[str, str]) -> Dict[str, Any]:
    """
    Process OA submission and calculate score.
    """
    try:
        # Validate timing again
        processes = await db_manager.get_collection("Processes")
        process_data = await processes.find_one({"_id": ObjectId(process_id)})
        
        if not process_data:
            return {"success": False, "message": "Process not found"}
        
        assessment_date = process_data.get("assessment_date")
        if assessment_date:
            from datetime import timedelta
            import pytz
            
            ist_tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist_tz)
            
            if assessment_date.tzinfo is None:
                assessment_date = ist_tz.localize(assessment_date)
            
            oa_start = assessment_date - timedelta(hours=OA_WINDOW_HOURS)
            oa_end = assessment_date
            
            if now < oa_start or now > oa_end:
                return {"success": False, "message": "Assessment window has closed"}
        
        # Validate application
        applications = await db_manager.get_collection("applications")
        application = await applications.find_one({
            "candidate_id": candidate_id,
            "process_id": process_id,
            "status": "Resume_shortlisted"
        })
        
        if not application:
            return {"success": False, "message": "Application not found or not eligible"}
        
        if application.get("oa_score") is not None:
            return {"success": False, "message": "Assessment already completed"}
        
        # Calculate score
        correct_count = 0
        total_questions = len(CORRECT_ANSWERS)
        
        for question, correct_answer in CORRECT_ANSWERS.items():
            if answers.get(question) == correct_answer:
                correct_count += 1
        
        score = int((correct_count / total_questions) * 100)
        
        # Only save score, don't change status yet (wait for OA deadline job)
        await applications.update_one(
            {"candidate_id": candidate_id, "process_id": process_id},
            {
                "$set": {
                    "oa_score": score,
                    "updated_at": datetime.now()
                }
            }
        )
        
        # Don't send email notification immediately - will be handled by scheduler
        
        return {
            "success": True,
            "message": "Assessment submitted successfully. Results will be communicated via email."
        }
        
    except Exception as e:
        return {"success": False, "message": f"Error processing submission: {str(e)}"}