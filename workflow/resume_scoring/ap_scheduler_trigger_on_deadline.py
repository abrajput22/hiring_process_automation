"""
Simple APScheduler for hiring process deadlines.
"""

import os
from datetime import datetime
from typing import Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from .resume_shortlisting_workflow import run_resume_scoring_workflow
from ..assessment_workflow import process_oa_deadline
from ..final_shortlisting_workflow import process_interview_deadline


async def execute_resume_workflow(process_id: str, process_name: str):
    """Execute resume scoring workflow."""
    try:
        print(f"APScheduler: Resume workflow for {process_name}")
        result = await run_resume_scoring_workflow(process_id)
        print(f"Resume workflow completed: {result.get('results', {}).get('shortlisted_candidates', 0)} shortlisted")
    except Exception as e:
        print(f"Resume workflow error: {e}")


async def execute_oa_deadline(process_id: str, process_name: str):
    """Execute OA deadline processing."""
    try:
        print(f"APScheduler: OA deadline for {process_name}")
        result = await process_oa_deadline(process_id)
        print(f"OA processing completed: {result.get('cleared_count', 0)} cleared")
    except Exception as e:
        print(f"OA processing error: {e}")


async def execute_interview_deadline(process_id: str, process_name: str):
    """Execute interview deadline processing - final shortlisting."""
    try:
        print(f"APScheduler: Interview deadline for {process_name}")
        result = await process_interview_deadline(process_id)
        print(f"Final shortlisting completed: {result.get('selected_count', 0)} selected")
    except Exception as e:
        print(f"Interview deadline error: {e}")


# Global scheduler
scheduler = AsyncIOScheduler(
    jobstores={'default': MongoDBJobStore(host=os.getenv('MONGODB_URI'), collection='scheduler_jobs')},
    executors={'default': AsyncIOExecutor()},
    timezone='Asia/Kolkata'
)


def start_scheduler():
    """Start scheduler."""
    scheduler.start()
    print("Scheduler started")


def stop_scheduler():
    """Stop scheduler."""
    scheduler.shutdown()
    print("Scheduler stopped")


async def schedule_process(process_doc: Dict[str, Any]):
    """Schedule jobs for a process."""
    import pytz
    
    process_id = str(process_doc["_id"])
    process_name = process_doc.get("process_name", "Unknown")
    ist_tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist_tz)
    
    # Schedule resume deadline
    resume_deadline = process_doc["resume_deadline"]
    if resume_deadline.tzinfo is None:
        resume_deadline = ist_tz.localize(resume_deadline)
    
    if resume_deadline > now:
        scheduler.add_job(
            func=execute_resume_workflow,
            trigger=DateTrigger(run_date=resume_deadline),
            args=[process_id, process_name],
            id=f"resume_{process_id}",
            replace_existing=True
        )
        print(f"Scheduled resume job for {process_name}")
    
    # Schedule OA deadline
    assessment_date = process_doc.get("assessment_date")
    if assessment_date:
        if assessment_date.tzinfo is None:
            assessment_date = ist_tz.localize(assessment_date)
        
        if assessment_date > now:
            scheduler.add_job(
                func=execute_oa_deadline,
                trigger=DateTrigger(run_date=assessment_date),
                args=[process_id, process_name],
                id=f"oa_{process_id}",
                replace_existing=True
            )
            print(f"Scheduled OA job for {process_name}")
    
    # Schedule interview deadline
    interview_date = process_doc.get("offline_interview_date")
    if interview_date:
        if interview_date.tzinfo is None:
            interview_date = ist_tz.localize(interview_date)
        
        if interview_date > now:
            scheduler.add_job(
                func=execute_interview_deadline,
                trigger=DateTrigger(run_date=interview_date),
                args=[process_id, process_name],
                id=f"interview_{process_id}",
                replace_existing=True
            )
            print(f"Scheduled interview deadline job for {process_name}")


def unschedule_process(process_id: str):
    """Remove jobs for a process."""
    try:
        scheduler.remove_job(f"resume_{process_id}")
        scheduler.remove_job(f"oa_{process_id}")
        scheduler.remove_job(f"interview_{process_id}")
        print(f"Unscheduled jobs for {process_id}")
    except:
        pass