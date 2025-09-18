"""
Webhook controller for deadline scheduling operations.
Handles scheduling and unscheduling of deadline-based workflow jobs.
"""

from fastapi import HTTPException
from workflow.resume_scoring.ap_scheduler_trigger_on_deadline import (
    schedule_process,
    unschedule_process
)


async def schedule_deadline_webhook(process_id: str):
    """Webhook to schedule a process for deadline execution."""
    try:
        from db_manager import db_manager
        from bson import ObjectId
        
        processes = await db_manager.get_collection("Processes")
        process_doc = await processes.find_one({"_id": ObjectId(process_id)})
        
        if not process_doc:
            raise HTTPException(status_code=404, detail="Process not found")
        
        await schedule_process(process_doc)
        return {"message": f"Process {process_id} scheduled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")


async def unschedule_deadline_webhook(process_id: str):
    """Webhook to unschedule a process deadline."""
    try:
        unschedule_process(process_id)
        return {"message": f"Process {process_id} unscheduled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unscheduling failed: {str(e)}")


async def get_scheduled_jobs_webhook():
    """Webhook to get all scheduled deadline jobs."""
    try:
        from workflow.resume_scoring.ap_scheduler_trigger_on_deadline import scheduler
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            })
        return {"scheduled_jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get jobs: {str(e)}")