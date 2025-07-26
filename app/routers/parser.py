from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
import tempfile, os, re, docx2txt
from datetime import datetime
from uuid import uuid4
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from bson import ObjectId
import google.generativeai as genai
from typing import List, Optional

from app.utils import extract_text_from_pdf, clean_json_output, extract_links_from_pdf
from app.prompts.prompts import RESUME_EXTRACTION_PROMPT, RESUME_RANKING_PROMPT, SCREENING_QUESTIONS_PROMPT
from config import settings
from app.db.mongo import collection
from app.dependencies.auth import get_current_user

load_dotenv()
genai.configure(api_key=settings.GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash-lite")

router = APIRouter()

def convert_objectid(obj):
    """Convert ObjectId and datetime objects to JSON serializable format"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid(i) for i in obj]
    return obj

def determine_file_type(file: UploadFile) -> str:
    """Determine file type from content_type or filename with enhanced detection"""
    content_type = file.content_type or ""
    filename = file.filename or ""
    
    # Log for debugging
    print(f"File analysis - Name: '{filename}', Content-Type: '{content_type}'")
    
    # Direct content type mapping
    if content_type == "application/pdf":
        return "pdf"
    elif content_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
    ]:
        return "docx"
    elif content_type and content_type.startswith("text/"):
        return "txt"
    
    # Enhanced fallback to file extension
    if filename and '.' in filename:
        # Handle cases where filename might have spaces or special characters
        clean_filename = filename.strip().lower()
        if clean_filename.endswith('.pdf'):
            return "pdf"
        elif clean_filename.endswith(('.docx', '.doc')):
            return "docx"
        elif clean_filename.endswith('.txt'):
            return "txt"
    
    # Additional checks for common issues
    if not filename or filename == 'file':
        raise HTTPException(
            status_code=400, 
            detail="Invalid filename. Please ensure your file has a proper name with extension (.pdf, .docx, .txt)"
        )
    
    return "unknown"

async def extract_text_from_resume(file: UploadFile) -> tuple[str, dict]:
    """Extract text and links from resume with robust error handling"""
    content = await file.read()
    file_type = determine_file_type(file)
    
    try:
        if file_type == "pdf":
            text = extract_text_from_pdf(content)
            links = extract_links_from_pdf(content)
        elif file_type == "docx":
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
                tmp.write(content)
                tmp.flush()
                text = docx2txt.process(tmp.name).strip()
                # Clean up temp file
                os.unlink(tmp.name)
            links = {"linkedin": "", "github": ""}
        elif file_type == "txt":
            text = content.decode("utf-8", errors='replace').strip()
            links = {"linkedin": "", "github": ""}
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Please upload PDF, DOCX, or TXT files. "
                       f"Content-Type: '{file.content_type}', Filename: '{file.filename}'"
            )
        
        return text, links
    
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File encoding not supported. Please save as UTF-8.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

def extract_fields_from_text(text: str) -> dict:
    """Extract structured data from resume text using Gemini"""
    prompt = RESUME_EXTRACTION_PROMPT + "\n\nResume:\n" + text
    try:
        response = model.generate_content(
            contents=[{"parts": [{"text": prompt}]}],
            generation_config={"temperature": 0}
        )
        return clean_json_output(response.text)
    except Exception as e:
        print(f"Gemini API error: {e}")
        return {}

def rank_resume_against_job(resume_text: str, job_description: str) -> dict:
    """Rank resume against job description using Gemini"""
    prompt = RESUME_RANKING_PROMPT.format(
        job_description=job_description,
        resume_text=resume_text
    )
    try:
        response = model.generate_content(
            contents=[{"parts": [{"text": prompt}]}],
            generation_config={"temperature": 0.1}
        )
        return clean_json_output(response.text)
    except Exception as e:
        print(f"Gemini ranking error: {e}")
        return {
            "overall_score": 0,
            "criteria_scores": {
                "skills_match": 0,
                "experience_relevance": 0,
                "education_fit": 0,
                "additional_qualifications": 0
            },
            "analysis": "Error occurred during ranking analysis"
        }

def generate_screening_questions(resume_data: dict, job_description: str) -> List[str]:
    """Generate screening questions using Gemini"""
    candidate_name = resume_data.get("personal_information", {}).get("full_name", "Candidate")
    skills = resume_data.get("professional_summary", {}).get("skills", [])
    experience = resume_data.get("experience", [])
    
    prompt = SCREENING_QUESTIONS_PROMPT.format(
        candidate_name=candidate_name,
        job_description=job_description,
        skills=", ".join(skills[:10]),  # Top 10 skills
        recent_experience=experience[0] if experience else {"role": "N/A", "company": "N/A"}
    )
    
    try:
        response = model.generate_content(
            contents=[{"parts": [{"text": prompt}]}],
            generation_config={"temperature": 0.3}
        )
        
        questions_data = clean_json_output(response.text)
        return questions_data.get("questions", [
            "Tell us about your relevant experience for this role.",
            "What interests you most about this position?",
            "How do you stay updated with industry trends?",
            "Describe a challenging project you've worked on.",
            "How do you handle tight deadlines and pressure?"
        ])
    except Exception as e:
        print(f"Questions generation error: {e}")
        return [
            "Tell us about your relevant experience for this role.",
            "What interests you most about this position?",
            "How do you stay updated with industry trends?",
            "Describe a challenging project you've worked on.",
            "How do you handle tight deadlines and pressure?"
        ]

@router.post("/parse-resume/")
async def parse_resume(
    file: UploadFile = File(...),
    user_email: str = Depends(get_current_user)
):
    """Parse resume and extract structured data"""
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Log file info for debugging
    print(f"Processing file: {file.filename}, Content-Type: {file.content_type}, Size: {file.size}")
    
    # Extract text and links
    text, links = await extract_text_from_resume(file)
    
    if not text or len(text.strip()) < 100:
        raise HTTPException(status_code=400, detail="Resume appears empty or unreadable. Please ensure the file contains readable text.")

    # Extract structured data using Gemini
    extracted_data = extract_fields_from_text(text)
    if not extracted_data:
        raise HTTPException(status_code=500, detail="Failed to parse resume. Please try again or contact support.")

    # Personal Information validation
    pi = extracted_data.setdefault("personal_information", {})
    for field in ["full_name", "email", "phone", "location", "linkedin", "github", "date_of_birth"]:
        pi.setdefault(field, "")

    # Validate email format
    if pi["email"] and not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", pi["email"]):
        pi["email"] = ""  # Clear invalid email instead of raising error

    # Clean and validate phone number
    if pi["phone"]:
        raw = pi["phone"].replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        cleaned = re.sub(r"^\+91", "", raw)
        if re.fullmatch(r"\d{10}", cleaned):
            pi["phone"] = cleaned
        else:
            pi["phone"] = ""  # Clear invalid phone instead of raising error

    # Validate date of birth format
    if pi["date_of_birth"] and not re.fullmatch(r"\d{2}-\d{2}-\d{4}", pi["date_of_birth"]):
        pi["date_of_birth"] = ""  # Clear invalid date instead of raising error

    # Fix LinkedIn and GitHub links
    for field in ["linkedin", "github"]:
        val = pi.get(field, "").strip()
        if not val and links.get(field):
            pi[field] = links[field]
        elif val and not val.startswith("http"):
            if "linkedin.com" in val.lower():
                pi[field] = "https://" + val.replace("://", "")
            elif "github.com" in val.lower():
                pi[field] = "https://" + val.replace("://", "")
        # Ensure empty fields are stored as empty strings, not None
        if not pi[field]:
            pi[field] = ""

    # Initialize data structures
    summary = extracted_data.setdefault("professional_summary", {})
    summary.setdefault("summary", "")
    summary.setdefault("skills", [])
    summary.setdefault("languages", [])

    for ed in extracted_data.setdefault("education", []):
        for field in ["degree", "college_university", "stream_field", "year_period", "grade_cgpa_percentage"]:
            ed.setdefault(field, "")

    for xp in extracted_data.setdefault("experience", []):
        for field in ["company", "role", "period", "description"]:
            xp.setdefault(field, "")

    for prj in extracted_data.setdefault("projects", []):
        for field in ["project_title", "technologies_course_semester", "description"]:
            prj.setdefault(field, "")
        for field in ["url", "start_end_date", "outcome_impact", "team_size", "budget_or_size"]:
            prj.setdefault(field, "")
        prj.setdefault("key_activities", [])
        prj.setdefault("certificate", {
            "file_name": "",
            "file_path": "",
            "uploaded_at": ""
        })

    extracted_data.setdefault("relevant_coursework", [])
    extracted_data.setdefault("certifications", [])
    extracted_data.setdefault("extracurricular_hobbies", [])

    # Store additional metadata (FIX: Store datetime as ISO string)
    extracted_data["original_text"] = text
    extracted_data["uploaded_by"] = user_email
    extracted_data["uploaded_at"] = datetime.utcnow().isoformat()  # Convert to ISO string immediately
    extracted_data["file_name"] = file.filename
    extracted_data["file_type"] = determine_file_type(file)
    
    try:
        result = collection.insert_one(extracted_data)
        
        # Create response data without datetime objects
        response_data = convert_objectid(extracted_data)
        
        return JSONResponse(content={
            "message": "Resume parsed successfully.",
            "inserted_id": str(result.inserted_id),
            "data": response_data
        })
    except Exception as e:
        print(f"Database insertion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/rank-resumes/")
async def rank_resumes(
    job_description: str = Form(...),
    limit: Optional[int] = Form(10),
    user_email: str = Depends(get_current_user)
):
    """Rank all user's resumes against a job description"""
    
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty")
    
    if limit and (limit < 1 or limit > 100):
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
    
    # Get all user's resumes
    try:
        user_resumes = list(collection.find({"uploaded_by": user_email}))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    if not user_resumes:
        raise HTTPException(status_code=404, detail="No resumes found for this user")
    
    rankings = []
    successful_rankings = 0
    
    for resume in user_resumes:
        resume_text = resume.get("original_text", "")
        if not resume_text:
            continue
            
        try:
            # Rank this resume against the job
            ranking_result = rank_resume_against_job(resume_text, job_description)
            
            candidate_name = resume.get("personal_information", {}).get("full_name", "Unknown")
            candidate_email = resume.get("personal_information", {}).get("email", "")
            
            # FIX: Ensure all data is JSON serializable
            uploaded_at = resume.get("uploaded_at", "")
            if isinstance(uploaded_at, datetime):
                uploaded_at = uploaded_at.isoformat()
            
            rankings.append({
                "resume_id": str(resume["_id"]),
                "candidate_name": candidate_name,
                "candidate_email": candidate_email,
                "overall_score": ranking_result.get("overall_score", 0),
                "criteria_scores": ranking_result.get("criteria_scores", {}),
                "analysis": ranking_result.get("analysis", ""),
                "skills": resume.get("professional_summary", {}).get("skills", [])[:5],
                "experience_years": len(resume.get("experience", [])),
                "education": resume.get("education", [{}])[0].get("degree", "") if resume.get("education") else "",
                "uploaded_at": uploaded_at  # Now guaranteed to be a string
            })
            successful_rankings += 1
            
        except Exception as e:
            print(f"Error ranking resume {resume['_id']}: {e}")
            continue
    
    # Sort by overall score (highest first)
    rankings.sort(key=lambda x: x["overall_score"], reverse=True)
    
    # Apply limit
    if limit:
        rankings = rankings[:limit]
    
    # FIX: Apply convert_objectid to the entire response to ensure JSON serialization
    response_data = {
        "message": f"Successfully ranked {successful_rankings} out of {len(user_resumes)} resumes",
        "job_description": job_description,
        "rankings": rankings,
        "total_resumes": len(user_resumes),
        "successful_rankings": successful_rankings
    }
    
    return JSONResponse(content=convert_objectid(response_data))

@router.post("/generate-questions/")
async def generate_questions(
    resume_id: str = Form(...),
    job_description: str = Form(...),
    user_email: str = Depends(get_current_user)
):
    """Generate screening questions for a specific candidate"""
    
    if not ObjectId.is_valid(resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume ID format")
    
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty")
    
    # Get the specific resume
    try:
        resume = collection.find_one({
            "_id": ObjectId(resume_id),
            "uploaded_by": user_email
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found or access denied")
    
    # Generate questions
    try:
        questions = generate_screening_questions(resume, job_description)
        candidate_name = resume.get("personal_information", {}).get("full_name", "Candidate")
        
        return JSONResponse(content={
            "message": "Screening questions generated successfully",
            "candidate_name": candidate_name,
            "resume_id": resume_id,
            "questions": questions,
            "total_questions": len(questions),
            "job_description": job_description
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating questions: {str(e)}")

@router.get("/my-resumes/")
async def get_my_resumes(user_email: str = Depends(get_current_user)):
    """Get all resumes for the current user with complete data"""
    
    try:
        # Fetch ALL fields instead of limited projection
        resumes = list(collection.find(
            {"uploaded_by": user_email}
            # Remove the projection to get ALL fields
        ).sort("uploaded_at", -1))
        
        return JSONResponse(content={
            "message": f"Found {len(resumes)} resumes",
            "resumes": convert_objectid(resumes),
            "total_count": len(resumes)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/project/upload-certificate")
async def upload_project_certificate(
    project_title: str = Form(...),
    certificate_file: UploadFile = File(...),
    user_email: str = Depends(get_current_user)
):
    """Upload certificate for a project"""
    
    # Validate file type
    allowed_types = ["application/pdf", "image/png", "image/jpeg", "image/jpg"]
    if certificate_file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail="Only PDF, PNG, or JPG files are allowed for certificates"
        )
    
    if not certificate_file.filename:
        raise HTTPException(status_code=400, detail="No certificate file uploaded")
    
    try:
        # Create unique filename
        ext = os.path.splitext(certificate_file.filename)[1]
        unique_filename = f"{uuid4().hex}{ext}"
        save_path = f"uploads/certificates/{unique_filename}"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # Save file
        with open(save_path, "wb") as f:
            f.write(await certificate_file.read())

        # Prepare certificate data
        cert_data = {
            "file_name": certificate_file.filename,
            "file_path": save_path,
            "uploaded_at": datetime.utcnow().isoformat()
        }

        # Update database
        result = collection.update_one(
            {
                "uploaded_by": user_email,
                "projects.project_title": project_title
            },
            {
                "$set": {
                    "projects.$.certificate": cert_data
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Project not found for this user")
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Certificate was not updated. Project may already have this certificate.")

        return JSONResponse(content={
            "message": "Certificate uploaded and linked to project successfully.",
            "project_title": project_title,
            "certificate_filename": certificate_file.filename,
            "file_path": save_path
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading certificate: {str(e)}")
