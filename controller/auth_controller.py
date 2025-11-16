"""
Controller for authentication functionality.
Handles user signup, login, and authentication-related operations.
"""

import asyncio
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr
from db_schema import Candidate
from db_manager import db_manager
from bson import ObjectId
import pymongo.errors


# Pydantic models for request/response bodies
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserDB(BaseModel):
    email: EmailStr
    role: str
    candidate_id: str | None = None


async def handle_signup(user_data: UserCreate):
    """Handle user signup and create candidate record."""
    for attempt in range(3):
        try:
            candidates_collection = await db_manager.get_collection("candidate")

            existing = await candidates_collection.find_one({"email": user_data.email})
            if existing:
                raise HTTPException(status_code=400, detail="Email already registered")

            candidate_state = Candidate(
                name=user_data.name,
                email=user_data.email,
                password=user_data.password,
                role=user_data.role,
            )
            result = await candidates_collection.insert_one(candidate_state.dict())
            return {"message": "User created successfully", "candidate_id": str(result.inserted_id)}
            
        except (pymongo.errors.NetworkTimeout, pymongo.errors.ServerSelectionTimeoutError) as e:
            if attempt == 2:
                raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
            await asyncio.sleep(1)


async def handle_login(user_data: UserLogin) -> UserDB:
    """Handle user login and return user data."""
    for attempt in range(3):
        try:
            candidates_collection = await db_manager.get_collection("candidate")
            candidate = await candidates_collection.find_one({"email": user_data.email})
            
            if candidate and user_data.password == candidate.get("password"):
                cid = str(candidate.get("_id")) if isinstance(candidate.get("_id"), ObjectId) else str(candidate.get("_id"))
                role = candidate.get("role") or "candidate"
                return UserDB(email=candidate.get("email"), role=role, candidate_id=cid)
            
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        except (pymongo.errors.NetworkTimeout, pymongo.errors.ServerSelectionTimeoutError) as e:
            if attempt == 2:
                raise HTTPException(status_code=503, detail="Database connection failed. Please try again later.")
            await asyncio.sleep(1)


async def handle_create_candidate(candidate: Candidate):
    """Deprecated: candidate is created during signup."""
    raise HTTPException(status_code=410, detail="Endpoint deprecated. Candidate is initialized during signup.")
