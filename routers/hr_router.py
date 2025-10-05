from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
import os

from controller.process_controller import create_hiring_process, list_hiring_processes, shortlist_process_candidates, get_process_detail, sync_application_status, delete_hiring_process, get_oa_shortlisted_candidates, save_hr_scores, execute_final_shortlisting, trigger_oa_workflow, trigger_final_workflow
from controller.workflow_controller import trigger_workflow
from controller.webhook_controller import schedule_deadline_webhook, unschedule_deadline_webhook, get_scheduled_jobs_webhook
from middleware.auth_middleware import User, require_hr
from db_schema import HiringProcess

def _view_path(filename: str) -> str:
    return os.path.join(os.path.dirname(__file__), "..", "views", filename)

router = APIRouter()

# Hiring process routes
@router.post("/{hr_id}/create_process")  # Called by: HR create form | Returns: New process confirmation
async def create_process(hr_id: str, process: HiringProcess, user: User = Depends(require_hr)):
    process.hr_id = hr_id
    return await create_hiring_process(process)

# More specific routes first
@router.post("/{hr_id}/processes/{process_id}/shortlist")  # Called by: HR shortlist button | Returns: Shortlisted candidates list
async def shortlist_candidates(hr_id: str, process_id: str, user: User = Depends(require_hr)):
    from datetime import datetime
    print(f"🔥 T0: Button clicked - Route hit at {datetime.now()}")
    result = await shortlist_process_candidates(process_id)
    print(f"🏁 T_FINAL: Workflow complete at {datetime.now()}")
    return result

@router.post("/{hr_id}/processes/{process_id}/trigger-workflow")  # Called by: HR workflow trigger | Returns: Workflow execution status
async def trigger_workflow_endpoint(hr_id: str, process_id: str, user: User = Depends(require_hr)):
    return await trigger_workflow(process_id)

@router.post("/{hr_id}/processes/{process_id}/sync-status")  # Called by: HR sync button | Returns: Updated application statuses
async def sync_status_endpoint(hr_id: str, process_id: str, user: User = Depends(require_hr)):
    return await sync_application_status(process_id)

@router.post("/{hr_id}/processes/{process_id}/schedule-deadline")  # Called by: HR schedule button | Returns: Scheduled job confirmation
async def schedule_deadline_endpoint(hr_id: str, process_id: str, user: User = Depends(require_hr)):
    return await schedule_deadline_webhook(process_id)

@router.delete("/{hr_id}/processes/{process_id}/schedule-deadline")  # Called by: HR unschedule button | Returns: Unschedule confirmation
async def unschedule_deadline_endpoint(hr_id: str, process_id: str, user: User = Depends(require_hr)):
    return await unschedule_deadline_webhook(process_id)

@router.get("/{hr_id}/scheduled-jobs")  # Called by: HR jobs page | Returns: List of all scheduled jobs
async def get_scheduled_jobs_endpoint(hr_id: str, user: User = Depends(require_hr)):
    return await get_scheduled_jobs_webhook()

@router.delete("/{hr_id}/processes/{process_id}")  # Called by: HR delete button | Returns: Delete confirmation
async def delete_process(hr_id: str, process_id: str, user: User = Depends(require_hr)):
    return await delete_hiring_process(process_id)

@router.get("/{hr_id}/processes/{process_id}")  # Called by: HR process detail page | Returns: Process details and applications
async def get_process(hr_id: str, process_id: str, user: User = Depends(require_hr)):
    return await get_process_detail(process_id)

@router.get("/api/{hr_id}/processes/{process_id}/oa-shortlisted")  # Called by: HR scoring page | Returns: OA shortlisted candidates
async def get_oa_shortlisted(hr_id: str, process_id: str, user: User = Depends(require_hr)):
    return await get_oa_shortlisted_candidates(process_id)

@router.post("/{hr_id}/processes/{process_id}/save-hr-scores")  # Called by: HR scoring page | Returns: Save confirmation
async def save_scores(hr_id: str, process_id: str, scores: dict, user: User = Depends(require_hr)):
    return await save_hr_scores(process_id, scores["scores"])

@router.post("/{hr_id}/processes/{process_id}/final-shortlist")  # Called by: HR scoring page | Returns: Final shortlisting results
async def final_shortlist(hr_id: str, process_id: str, user: User = Depends(require_hr)):
    return await execute_final_shortlisting(process_id)

@router.post("/{hr_id}/processes/{process_id}/trigger-oa-workflow")  # Called by: HR process detail page | Returns: OA workflow results
async def trigger_oa_workflow_endpoint(hr_id: str, process_id: str, user: User = Depends(require_hr)):
    return await trigger_oa_workflow(process_id)

@router.post("/{hr_id}/processes/{process_id}/trigger-final-workflow")  # Called by: HR process detail page | Returns: Final workflow results
async def trigger_final_workflow_endpoint(hr_id: str, process_id: str, user: User = Depends(require_hr)):
    return await trigger_final_workflow(process_id)

# Less specific routes after
@router.get("/api/{hr_id}/processes")  # Called by: HR dashboard | Returns: List of all HR's processes
async def get_processes(hr_id: str, user: User = Depends(require_hr)):
    return await list_hiring_processes(hr_id)

@router.get("/{hr_id}/processes")  # Called by: HR redirect | Returns: List of all HR's processes
async def get_processes_redirect(hr_id: str, user: User = Depends(require_hr)):
    return await list_hiring_processes(hr_id)

# HR endpoint to view applications to their processes
@router.get("/{hr_id}/applications")  # Called by: HR applications page | Returns: All applications to HR's processes
async def get_hr_applications(hr_id: str, user: User = Depends(require_hr)):
    return {"message": "HR applications view - not implemented yet", "hr_id": hr_id}

# HR views - move to end to avoid conflicts
@router.get("/{hr_id}/show_all_processes")  # Called by: Browser navigation | Returns: HR processes list HTML page
async def serve_list_processes_view(hr_id: str):
    return FileResponse(_view_path("hr_list_processes.html"))

@router.get("/{hr_id}/show_process_detail/{process_id}")  # Called by: Browser navigation | Returns: Process detail HTML page
async def serve_process_detail_view(hr_id: str, process_id: str):
    return FileResponse(_view_path("hr_process_detail.html"))

@router.get("/{hr_id}/home")  # Called by: Browser navigation | Returns: HR home HTML page
async def serve_hr_home_page(hr_id: str):
    return FileResponse(_view_path("home.html"))

@router.get("/{hr_id}/create_process")  # Called by: Browser navigation | Returns: Create process HTML form
async def serve_create_process_view(hr_id: str):
    return FileResponse(_view_path("hr_create_process.html"))

@router.get("/{hr_id}/processes/{process_id}/scoring")  # Called by: Browser navigation | Returns: HR scoring HTML page
async def serve_hr_scoring_view(hr_id: str, process_id: str):
    return FileResponse(_view_path("hr_scoring.html"))