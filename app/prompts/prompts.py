
RESUME_EXTRACTION_PROMPT = """
You will be given a resume document. Your task is to extract the following specific fields and return them in a clean and fixed JSON structure. 

Do NOT include any additional sections or explanations. Only extract the exact keys mentioned below and populate them with actual values from the resume if available, otherwise leave them empty (as empty strings, arrays, or objects), with the following exception:

Extract LinkedIn and GitHub as full URLs if present anywhere in the resume. 
Make sure they begin with "https://" and are complete, copy-pasted from the resume, not summarized.

> Exception: For the field `projects[*].description`, if no description is found in the resume, intelligently generate a concise and informative 2–3 line description based on the project title, technologies used, or context. Do NOT leave it blank.

### Output Requirements:
- Return a valid, parsable JSON object only (no code blocks or markdown).
- Validate and include full URLs for LinkedIn and GitHub if present.
- Phone number and email must be in correct formats.
- Preserve the exact structure and field names as shown below.

### Fixed JSON Format:
{
  "personal_information": {
    "full_name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "github": "",
    "date_of_birth": ""
  },
  "professional_summary": {
    "summary": "",
    "skills": [],
    "languages": []
  },
  "education": [
    {
      "degree": "",
      "college_university": "",
      "stream_field": "",
      "year_period": "",
      "grade_cgpa_percentage": ""
    }
  ],
  "relevant_coursework": [],
  "experience": [
    {
      "company": "",
      "role": "",
      "period": "",
      "description": ""
    }
  ],
  "projects": [
    {
      "project_title": "",
      "technologies_course_semester": "",
      "description": "",
      "url": "",
      "client_name": "",
      "start_end_date": "",
      # "key_activities": [],
      "outcome_impact": "",
      "team_size": "",
      "budget_or_size": "",
      "certificate": {
        "file_name": "",
        "file_path": "",
        "uploaded_at": ""
        }
    }
  ],
  "certifications": [],
  "extracurricular_hobbies": []
}

If the resume is malformed, unreadable, or empty, return:
{
  "error": "Resume could not be parsed due to invalid format or empty content."
}
"""

RESUME_RANKING_PROMPT = """
You are an expert HR professional. Analyze the following resume against the job description and provide a detailed ranking.

Job Description:
{job_description}

Resume:
{resume_text}

Evaluate the resume on these criteria (0-100 scale):
1. Skills Match - How well candidate's skills align with job requirements
2. Experience Relevance - Relevance and quality of work experience
3. Education Fit - Educational background alignment
4. Additional Qualifications - Certifications, projects, achievements

Return ONLY a valid JSON object with this exact structure:
{{
    "overall_score": 85,
    "criteria_scores": {{
        "skills_match": 90,
        "experience_relevance": 80,
        "education_fit": 85,
        "additional_qualifications": 75
    }},
    "analysis": "Detailed 2-3 sentence analysis of why this candidate fits the role, highlighting key strengths and any gaps."
}}
"""

SCREENING_QUESTIONS_PROMPT = """
You are an experienced recruiter. Generate 5-7 relevant screening questions for this candidate based on their resume and the job description.

Candidate: {candidate_name}
Job Description: {job_description}
Key Skills: {skills}
Recent Experience: {recent_experience}

Create questions that:
1. Test technical/functional competencies
2. Assess cultural fit
3. Explore motivation and interest
4. Validate key claims from resume
5. Understand career goals

Return ONLY a valid JSON object:
{{
    "questions": [
        "Question 1 here",
        "Question 2 here",
        "Question 3 here",
        "Question 4 here",
        "Question 5 here"
    ]
}}
"""

  