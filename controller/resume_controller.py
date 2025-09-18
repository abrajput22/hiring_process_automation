"""
Controller for resume functionality.
Handles all business logic related to resume submission and upload.
"""

from fastapi import HTTPException, UploadFile
from bson import ObjectId
from db_manager import db_manager
from db_schema import Candidate
from middleware.auth_middleware import User
import io
from typing import Optional
import pdfplumber
from PyPDF2 import PdfReader
from datetime import datetime

try:
    from docx import Document as DocxDocument
except Exception:
    DocxDocument = None


async def get_candidate_collection():
    """Get the candidate collection."""
    return await db_manager.get_collection("candidate")


async def extract_text_from_upload(file: UploadFile) -> str:
    """Extract text from uploaded file (PDF, TXT, DOCX)."""
    content_type = (file.content_type or '').lower()
    data = await file.read()
    # Reset for potential re-use
    try:
        file.file.seek(0)
    except Exception:
        pass

    if 'pdf' in content_type:
        # Prefer pdfplumber (text-based PDFs)
        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                texts = []
                for page in pdf.pages:
                    texts.append(page.extract_text() or '')
                text = "\n".join(texts).strip()
                if text:
                    return text
        except Exception:
            pass
        # Fallback to PyPDF2
        try:
            reader = PdfReader(io.BytesIO(data))
            texts = [page.extract_text() or '' for page in reader.pages]
            text = "\n".join(texts).strip()
            if text:
                return text
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="Unable to extract text from PDF. Ensure it is text-based, not scanned.")

    if 'text/plain' in content_type:
        try:
            return data.decode('utf-8', errors='ignore')
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to decode text file")

    if 'officedocument.wordprocessingml.document' in content_type:
        if not DocxDocument:
            raise HTTPException(status_code=400, detail="DOCX parsing not available on this server")
        try:
            doc = DocxDocument(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to extract text from DOCX")

    raise HTTPException(status_code=400, detail="Unsupported file type. Upload a text-based PDF, TXT, or DOCX.")


async def submit_resume(candidate_id: str, candidate_data: Candidate, user: User, process_id: str = None):
    """Submit resume for a candidate."""
    
    candidates_collection = await get_candidate_collection()
    applications_collection = await db_manager.get_collection("applications")

    if not candidate_data.email:
        raise HTTPException(status_code=400, detail="Email is required to submit resume")

    # Check deadline if process_id is provided
    if process_id:
        from bson import ObjectId
        from bson.errors import InvalidId
        processes_collection = await db_manager.get_collection("Processes")
        
        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(process_id):
                raise HTTPException(status_code=400, detail=f"Invalid process ID format: {process_id}")
                
            process = await processes_collection.find_one({"_id": ObjectId(process_id)})
            if not process:
                raise HTTPException(status_code=404, detail="Process not found")
            
            deadline = process.get("resume_deadline")
            if deadline and datetime.now() > deadline:
                raise HTTPException(status_code=400, detail="Application deadline has passed")
        except InvalidId:
            raise HTTPException(status_code=400, detail=f"Invalid process ID format: {process_id}")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

    # Update candidate record (no resume_text here anymore)
    update_doc = {"$set": {}}
    if candidate_data.name is not None:
        update_doc["$set"]["name"] = candidate_data.name
    
    if update_doc["$set"]:
        await candidates_collection.update_one(
            {"email": candidate_data.email},
            update_doc,
            upsert=True,
        )

    # Create or update application record if process_id is provided
    if process_id:
        
        # Get the candidate ID
        candidate_record = await candidates_collection.find_one({"email": candidate_data.email})
        if not candidate_record:
            raise HTTPException(status_code=404, detail="Candidate not found")
        actual_candidate_id = str(candidate_record["_id"])
        
        # Get temp resume text from candidate record
        temp_resume_text = candidate_record.get("temp_resume_text")
        
        # Update or create application with resume text
        update_data = {
            "status": "Applied",
            "updated_at": datetime.now()
        }
        if temp_resume_text:
            update_data["resume_text"] = temp_resume_text
            
        await applications_collection.update_one(
            {
                "candidate_id": actual_candidate_id,
                "process_id": process_id
            },
            {
                "$set": update_data,
                "$setOnInsert": {
                    "candidate_id": actual_candidate_id,
                    "process_id": process_id,
                    "created_at": datetime.now()
                }
            },
            upsert=True
        )
        
        # Clear temp resume text from candidate
        if temp_resume_text:
            await candidates_collection.update_one(
                {"_id": candidate_record["_id"]},
                {"$unset": {"temp_resume_text": ""}}
            )

    return {"message": "Resume stored. The AI agent will now begin processing."}


async def upload_resume_file(candidate_id: str, name: str = None, file: UploadFile = None, user: User = None, process_id: str = None):
    """Upload resume file for a candidate and store in application."""
    
    print(f"DEBUG: upload_resume_file called with process_id: {process_id}")
    
    candidates_collection = await get_candidate_collection()
    applications_collection = await db_manager.get_collection("applications")
    
    # Try to find existing candidate by ID or email
    cand = None
    try:
        cand = await candidates_collection.find_one({"_id": ObjectId(candidate_id)})
    except Exception:
        pass
    
    # If not found by ID, try by email
    if not cand and user and user.email:
        cand = await candidates_collection.find_one({"email": user.email})
        if cand:
            candidate_id = str(cand["_id"])  # Update candidate_id to match DB
    
    # If still not found, create a new candidate
    if not cand:
        candidate_doc = {
            "email": user.email if user else "unknown@example.com",
            "role": "candidate"
        }
        if name:
            candidate_doc["name"] = name
            
        result = await candidates_collection.insert_one(candidate_doc)
        candidate_id = str(result.inserted_id)
        cand = candidate_doc
        cand["_id"] = result.inserted_id

    resume_text = await extract_text_from_upload(file)

    # Update candidate name if provided
    if name is not None:
        await candidates_collection.update_one(
            {"_id": cand["_id"]}, 
            {"$set": {"name": name}}
        )

    # If process_id provided, check deadline and store resume directly in application
    if process_id:
        from bson import ObjectId
        from bson.errors import InvalidId
        processes_collection = await db_manager.get_collection("Processes")
        
        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(process_id):
                raise HTTPException(status_code=400, detail=f"Invalid process ID format: {process_id}")
                
            process = await processes_collection.find_one({"_id": ObjectId(process_id)})
            if not process:
                raise HTTPException(status_code=404, detail="Process not found")
            
            deadline = process.get("resume_deadline")
            if deadline and datetime.now() > deadline:
                raise HTTPException(status_code=400, detail="Application deadline has passed")
        except InvalidId:
            raise HTTPException(status_code=400, detail=f"Invalid process ID format: {process_id}")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
        
        await applications_collection.update_one(
            {
                "candidate_id": candidate_id,
                "process_id": process_id
            },
            {
                "$set": {
                    "resume_text": resume_text,
                    "status": "Applied",
                    "updated_at": datetime.now()
                },
                "$setOnInsert": {
                    "candidate_id": candidate_id,
                    "process_id": process_id,
                    "created_at": datetime.now()
                }
            },
            upsert=True
        )
    else:
        # Store temporarily if no process_id
        await candidates_collection.update_one(
            {"_id": cand["_id"]}, 
            {"$set": {"temp_resume_text": resume_text}}
        )

    return {"message": "Resume uploaded and extracted successfully.", "resume_length": len(resume_text)}