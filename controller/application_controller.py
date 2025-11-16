"""
Controller for application-specific operations.
Handles scoring and status updates per application.
"""

import asyncio
from fastapi import HTTPException
from bson import ObjectId
from datetime import datetime
from db_manager import db_manager
from middleware.auth_middleware import User
import pymongo.errors

async def update_application_scores(candidate_id: str, process_id: str, scores: dict, user: User = None):
    """Update scores for a specific application."""
    
    for attempt in range(3):
        try:
            applications = await db_manager.get_collection("applications")
            
            # Find the specific application
            application = await applications.find_one({
                "candidate_id": candidate_id,
                "process_id": process_id
            })
            
            if not application:
                raise HTTPException(status_code=404, detail="Application not found")
            
            # Prepare update document
            update_doc = {"$set": {"updated_at": datetime.now()}}
            
            # Update only provided scores
            if "resume_match_score" in scores:
                update_doc["$set"]["resume_match_score"] = scores["resume_match_score"]
            if "oa_score" in scores:
                update_doc["$set"]["oa_score"] = scores["oa_score"]
            if "tech_score" in scores:
                update_doc["$set"]["tech_score"] = scores["tech_score"]
            if "hr_score" in scores:
                update_doc["$set"]["hr_score"] = scores["hr_score"]
            if "status" in scores:
                update_doc["$set"]["status"] = scores["status"]
            
            await applications.update_one(
                {"_id": application["_id"]},
                update_doc
            )
            
            return {"message": "Application scores updated successfully"}
            
        except (pymongo.errors.NetworkTimeout, pymongo.errors.ServerSelectionTimeoutError) as e:
            if attempt == 2:
                raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
            await asyncio.sleep(1)

async def get_application_scores(candidate_id: str, process_id: str):
    """Get scores for a specific application."""
    
    for attempt in range(3):
        try:
            applications = await db_manager.get_collection("applications")
            
            application = await applications.find_one({
                "candidate_id": candidate_id,
                "process_id": process_id
            })
            
            if not application:
                raise HTTPException(status_code=404, detail="Application not found")
            
            return {
                "candidate_id": candidate_id,
                "process_id": process_id,
                "status": application.get("status"),
                "resume_match_score": application.get("resume_match_score"),
                "oa_score": application.get("oa_score"),
                "tech_score": application.get("tech_score"),
                "hr_score": application.get("hr_score"),
                "created_at": application.get("created_at"),
                "updated_at": application.get("updated_at")
            }
            
        except (pymongo.errors.NetworkTimeout, pymongo.errors.ServerSelectionTimeoutError) as e:
            if attempt == 2:
                raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
            await asyncio.sleep(1)