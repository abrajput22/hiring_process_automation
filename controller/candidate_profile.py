"""
Controller for candidate profile functionality.
Handles all business logic related to candidate profile management.
"""

import asyncio
from fastapi import HTTPException
from bson import ObjectId
from db_manager import db_manager
from db_schema import Candidate
from middleware.auth_middleware import User
from typing import Union, Any
import pymongo.errors


async def get_candidate_profile(candidate_id: str, user: User):
    """Get candidate/user profile information."""
    
    for attempt in range(3):
        try:
            candidates = await db_manager.get_collection("candidate")
            try:
                doc = await candidates.find_one({"_id": ObjectId(candidate_id)})
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid user id")
            
            if not doc:
                raise HTTPException(status_code=404, detail="User not found")
            
            doc["_id"] = str(doc["_id"])  # serialize id
            # Avoid exposing password and temp resume text
            if "password" in doc:
                del doc["password"]
            if "temp_resume_text" in doc:
                del doc["temp_resume_text"]
            
            return doc
            
        except (pymongo.errors.NetworkTimeout, pymongo.errors.ServerSelectionTimeoutError) as e:
            if attempt == 2:
                raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
            await asyncio.sleep(1)


async def update_candidate_profile(candidate_id: str, payload: Any, user: User):
    """Update candidate/user profile information."""
    
    for attempt in range(3):
        try:
            candidates = await db_manager.get_collection("candidate")
            try:
                oid = ObjectId(candidate_id)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid user id")

            update_fields = {}
            if hasattr(payload, 'name') and payload.name is not None:
                update_fields["name"] = payload.name
            if not update_fields:
                raise HTTPException(status_code=400, detail="No updatable fields provided")

            await candidates.update_one({"_id": oid}, {"$set": update_fields})
            return {"message": "Profile updated"}
            
        except (pymongo.errors.NetworkTimeout, pymongo.errors.ServerSelectionTimeoutError) as e:
            if attempt == 2:
                raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
            await asyncio.sleep(1)
