from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
import os
import asyncio
from datetime import datetime
import pytz
import json 

# Import routers
from routers.auth_router import router as auth_router
from routers.global_router import router as global_router
from routers.candidate_router import router as candidate_router
from routers.hr_router import router as hr_router
from routers.oa_router import router as oa_router

# Custom JSON encoder for IST timezone
class ISTJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            ist_tz = pytz.timezone('Asia/Kolkata')
            if obj.tzinfo is None:
                obj = ist_tz.localize(obj)
            else:
                obj = obj.astimezone(ist_tz)
            return obj.isoformat()
        return super().default(obj)

app = FastAPI(title="Global Hiring Agent API", version="1.0.0")



@app.on_event("startup")
async def startup_event():
    """Initialize APScheduler on app startup."""
    try:
        from workflow.resume_scoring.ap_scheduler_trigger_on_deadline import start_scheduler
        start_scheduler()
        print("APScheduler started successfully")
    except Exception as e:
        print(f"Failed to start APScheduler: {e}")
    


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup APScheduler on app shutdown."""
    try:
        from workflow.resume_scoring.ap_scheduler_trigger_on_deadline import stop_scheduler
        stop_scheduler()
        print("APScheduler stopped")
    except Exception as e:
        print(f"Error stopping APScheduler: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/public", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "public")), name="public")

# Include routers
app.include_router(auth_router)
app.include_router(global_router)
app.include_router(candidate_router)
app.include_router(hr_router)
app.include_router(oa_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

