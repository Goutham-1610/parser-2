import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.express as px

# Configuration
API_BASE_URL = "http://localhost:8000/api"

# Create a persistent session object
if 'session' not in st.session_state:
    st.session_state.session = requests.Session()

# Session state initialization
if 'authenticated' not in st.session_state:    
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# Set page config
st.set_page_config(
    page_title="🎯 LLM Resume Screener",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff6b6b;
    }
    .resume-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .score-high { color: #28a745; font-weight: bold; }
    .score-medium { color: #ffc107; font-weight: bold; }
    .score-low { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

def login_user(email, password):
    """Login using session cookies"""
    try:
        response = st.session_state.session.post(f"{API_BASE_URL}/login", 
                                               json={"email": email, "password": password})
        if response.status_code == 200:
            st.session_state.authenticated = True
            st.session_state.user_email = email
            return True, "Login successful!"
        else:
            return False, "Invalid credentials"
    except Exception as e:
        return False, f"Login error: {str(e)}"

def register_user(email, password):
    """Register new user"""
    try:
        response = st.session_state.session.post(f"{API_BASE_URL}/register", 
                                               json={"email": email, "password": password})
        if response.status_code == 200:
            return True, "Registration successful! Please login."
        else:
            error_detail = response.json().get('detail', 'Registration failed')
            return False, error_detail
    except Exception as e:
        return False, f"Registration error: {str(e)}"

def logout_user():
    """Logout user"""
    try:
        st.session_state.session.post(f"{API_BASE_URL}/logout")
    except:
        pass
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.session = requests.Session()

def login_page():
    """Login/Registration page"""
    st.title("🔐 LLM Resume Screener - Login")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login", use_container_width=True):
                if email and password:
                    success, message = login_user(email, password)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please enter both email and password")
    
    with tab2:
        st.subheader("Register")
        with st.form("register_form"):
            reg_email = st.text_input("Email", key="reg_email", placeholder="your@email.com")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            
            if st.form_submit_button("Register", use_container_width=True):
                if reg_email and reg_password:
                    success, message = register_user(reg_email, reg_password)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.warning("Please enter both email and password")

def upload_page():
    """Enhanced resume upload page with batch processing"""
    st.title("📤 Upload Resumes (Batch Processing)")
    st.write("Upload multiple candidate resumes for bulk processing and ranking")
    
    # Batch upload section
    uploaded_files = st.file_uploader(
        "Choose multiple resume files", 
        type=['pdf', 'docx', 'txt'],
        accept_multiple_files=True,
        help="Select multiple resumes to upload at once"
    )
    
    if uploaded_files:
        st.success(f"📁 {len(uploaded_files)} files selected for upload")
        
        # Display selected files
        with st.expander("📋 Selected Files Preview"):
            for i, file in enumerate(uploaded_files, 1):
                st.write(f"{i}. **{file.name}** ({file.size} bytes, {file.type})")
        
        # Batch processing button
        if st.button("🚀 Process All Resumes", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            successful_uploads = 0
            failed_uploads = []
            
            for i, uploaded_file in enumerate(uploaded_files):
                # Update progress
                progress = (i + 1) / len(uploaded_files)
                progress_bar.progress(progress)
                status_text.text(f"Processing {i+1}/{len(uploaded_files)}: {uploaded_file.name}")
                
                try:
                    # Extract candidate name from filename (basic approach)
                    candidate_name = uploaded_file.name.replace('.pdf', '').replace('.docx', '').replace('.txt', '')
                    candidate_email = f"candidate{i+1}@temp.com"  # Temporary email
                    
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type
                        )
                    }
                    data = {"name": candidate_name, "email": candidate_email}
                    
                    response = st.session_state.session.post(
                        f"{API_BASE_URL}/parse-resume/", 
                        files=files, 
                        data=data
                    )
                    
                    if response.status_code == 200:
                        successful_uploads += 1
                    else:
                        failed_uploads.append(uploaded_file.name)
                        
                except Exception as e:
                    failed_uploads.append(f"{uploaded_file.name}: {str(e)}")
            
            # Final results
            progress_bar.progress(1.0)
            status_text.text("✅ Batch processing completed!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("✅ Successful Uploads", successful_uploads)
            with col2:
                st.metric("❌ Failed Uploads", len(failed_uploads))
            
            if failed_uploads:
                with st.expander("❌ Failed Uploads Details"):
                    for failure in failed_uploads:
                        st.write(f"• {failure}")
            
            if successful_uploads > 0:
                st.success(f"🎉 Successfully processed {successful_uploads} resumes!")
                st.info("👉 Go to 'Rank & Screen' tab to rank all uploaded resumes against a job description")

def ranking_page():
    """Streamlined ranking page focused only on resume ranking"""
    st.title("🏆 Rank All Candidates")
    st.write("Compare and rank all uploaded resumes against job requirements")
    
    # Show available resumes count
    try:
        response = st.session_state.session.get(f"{API_BASE_URL}/my-resumes/")
        if response.status_code == 200:
            result = response.json()
            total_resumes = result.get('total_count', 0)
            
            st.info(f"📊 **{total_resumes} resumes** available for ranking")
            
            if total_resumes == 0:
                st.warning("⚠️ No resumes found. Please upload some resumes first.")
                return
                
        else:
            st.error("Failed to fetch resume count")
            return
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return
    
    # Job description input
    job_description = st.text_area(
        "Job Description",
        height=200,
        placeholder="Enter the complete job description including required skills, experience, qualifications...",
        help="Provide detailed job requirements for accurate candidate ranking"
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🔍 Rank All Candidates", use_container_width=True):
            if job_description.strip():
                rank_all_resumes(job_description, total_resumes)
            else:
                st.warning("⚠️ Please enter a job description")
    
    with col2:
        max_results = st.number_input("Max Results", min_value=1, max_value=50, value=min(total_resumes, 10))

def rank_all_resumes(job_description, total_count):
    """Rank all uploaded resumes against job description"""
    with st.spinner(f"🤖 AI is analyzing {total_count} resumes..."):
        try:
            response = st.session_state.session.post(f"{API_BASE_URL}/rank-resumes/",
                                   data={"job_description": job_description})
            
            if response.status_code == 200:
                result = response.json()
                rankings = result.get('rankings', [])
                successful_rankings = result.get('successful_rankings', 0)
                
                if rankings:
                    st.success(f"✅ Successfully ranked {successful_rankings}/{total_count} candidates")
                    
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("📊 Total Analyzed", successful_rankings)
                    with col2:
                        avg_score = sum(r['overall_score'] for r in rankings) / len(rankings)
                        st.metric("📈 Average Score", f"{avg_score:.1f}%")
                    with col3:
                        high_quality = sum(1 for r in rankings if r['overall_score'] >= 80)
                        st.metric("⭐ High Quality (80%+)", high_quality)
                    with col4:
                        top_score = max(r['overall_score'] for r in rankings) if rankings else 0
                        st.metric("🏆 Top Score", f"{top_score}%")
                    
                    # Score distribution chart
                    if len(rankings) > 1:
                        scores = [r['overall_score'] for r in rankings]
                        fig = px.histogram(
                            x=scores, 
                            nbins=10, 
                            title="📊 Score Distribution",
                            labels={'x': 'Score (%)', 'y': 'Number of Candidates'},
                            color_discrete_sequence=['#1f77b4']
                        )
                        fig.update_layout(showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    st.divider()
                    st.subheader("🏆 Candidate Rankings")
                    
                    # Display all rankings
                    for i, ranking in enumerate(rankings, 1):
                        display_simplified_ranking(ranking, i)
                        
                else:
                    st.warning("⚠️ No candidates could be ranked")
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                st.error(f"❌ Ranking failed: {error_detail}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

def display_simplified_ranking(ranking, position):
    """Display candidate ranking - FOCUSED ON RANKING ONLY"""
    score = ranking.get('overall_score', 0)
    name = ranking.get('candidate_name', 'Unknown')
    email = ranking.get('candidate_email', '')
    analysis = ranking.get('analysis', '')
    skills = ranking.get('skills', [])
    criteria_scores = ranking.get('criteria_scores', {})
    experience_years = ranking.get('experience_years', 0)
    education = ranking.get('education', '')
    
    # Color coding based on score
    if score >= 80:
        score_color = "#28a745"  # Green
        badge = "🥇"
    elif score >= 70:
        score_color = "#17a2b8"  # Blue
        badge = "🥈"
    elif score >= 60:
        score_color = "#ffc107"  # Yellow
        badge = "🥉"
    else:
        score_color = "#dc3545"  # Red
        badge = "📋"
    
    with st.container():
        # Header with score
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"""
            <div style="border-left: 4px solid {score_color}; padding-left: 15px; margin: 10px 0;">
                <h4>{badge} #{position} - {name}</h4>
                <p><strong>Email:</strong> {email}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.metric("Overall Score", f"{score}%", delta=None)
        
        # Detailed breakdown
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.write("**🤖 AI Analysis:**")
            st.write(analysis)
            
            if skills:
                st.write("**🛠️ Key Skills:**")
                skills_display = " • ".join(skills[:8])  # Show top 8 skills
                st.write(skills_display)
        
        with col2:
            # Criteria scores as progress bars
            if criteria_scores:
                st.write("**📊 Detailed Scores:**")
                for criteria, score_val in criteria_scores.items():
                    criteria_name = criteria.replace('_', ' ').title()
                    st.write(f"**{criteria_name}:** {score_val}%")
                    st.progress(score_val / 100)
            
            # Additional info
            st.write(f"**📈 Experience:** {experience_years} positions")
            if education:
                st.write(f"**🎓 Education:** {education}")
        
        st.divider()

def my_resumes_page():
    """Display user's uploaded resumes with complete data"""
    st.title("📂 My Resumes")
    st.write("View and manage your uploaded resumes")
    
    try:
        response = st.session_state.session.get(f"{API_BASE_URL}/my-resumes/")
        
        if response.status_code == 200:
            result = response.json()
            resumes = result.get('resumes', [])
            
            if resumes:
                st.success(f"📊 Found {len(resumes)} uploaded resumes")
                
                # Create a dataframe for better display
                resume_data = []
                for resume in resumes:
                    personal_info = resume.get('personal_information', {})
                    resume_data.append({
                        'Name': personal_info.get('full_name', 'N/A'),
                        'Email': personal_info.get('email', 'N/A'),
                        'Phone': personal_info.get('phone', 'N/A'),
                        'Upload Date': resume.get('uploaded_at', 'N/A'),
                        'Skills Count': len(resume.get('professional_summary', {}).get('skills', [])),
                        'Resume ID': str(resume.get('_id', ''))
                    })
                
                df = pd.DataFrame(resume_data)
                st.dataframe(df, use_container_width=True)
                
                # Resume details
                if len(resumes) > 0:
                    selected_resume = st.selectbox(
                        "Select resume for complete details:",
                        options=range(len(resumes)),
                        format_func=lambda x: f"{resume_data[x]['Name']} - {resume_data[x]['Phone']}"
                    )
                    
                    if selected_resume is not None:
                        display_complete_resume(resumes[selected_resume])
            else:
                st.info("📝 No resumes uploaded yet. Go to 'Upload Resumes' to get started!")
        else:
            st.error("❌ Failed to fetch resumes")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

def display_complete_resume(resume):
    """Display complete resume data with all fields"""
    with st.expander("📋 Complete Resume Details", expanded=True):
        # Personal Information Section - ENHANCED
        st.subheader("👤 Personal Information")
        personal_info = resume.get('personal_information', {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Full Name:** {personal_info.get('full_name', 'Not provided')}")
            st.write(f"**Email:** {personal_info.get('email', 'Not provided')}")
            st.write(f"**Phone:** {personal_info.get('phone', 'Not provided')}")
        with col2:
            st.write(f"**Location:** {personal_info.get('location', 'Not provided')}")
            st.write(f"**Date of Birth:** {personal_info.get('date_of_birth', 'Not provided')}")
        with col3:
            # Enhanced LinkedIn and GitHub display
            linkedin = personal_info.get('linkedin', 'Not provided')
            github = personal_info.get('github', 'Not provided')
            
            if linkedin and linkedin != 'Not provided' and linkedin != '':
                st.write(f"**LinkedIn:** [Profile Link]({linkedin})")
            else:
                st.write("**LinkedIn:** Not provided")
                
            if github and github != 'Not provided' and github != '':
                st.write(f"**GitHub:** [Profile Link]({github})")
            else:
                st.write("**GitHub:** Not provided")
        
        st.divider()
        
        # Professional Summary Section - COMPLETE
        st.subheader("📝 Professional Summary")
        prof_summary = resume.get('professional_summary', {})
        
        summary_text = prof_summary.get('summary', '')
        if summary_text and summary_text.strip():
            st.write("**Summary:**")
            st.write(summary_text)
        else:
            st.write("**Summary:** Not provided")
        
        skills = prof_summary.get('skills', [])
        if skills:
            st.write("**Skills:**")
            # Display skills as tags/chips
            skills_html = ""
            for skill in skills:
                skills_html += f'<span style="background-color: #2563eb; padding: 2px 8px; margin: 2px; border-radius: 12px; font-size: 12px;">{skill}</span> '
            st.markdown(skills_html, unsafe_allow_html=True)
        else:
            st.write("**Skills:** Not provided")
        
        languages = prof_summary.get('languages', [])
        if languages:
            st.write("**Languages:**")
            st.write(" • ".join(languages))
        else:
            st.write("**Languages:** Not provided")
        
        st.divider()
        
        # Experience Section - COMPLETE
        st.subheader("💼 Work Experience")
        experience = resume.get('experience', [])
        if experience:
            for i, exp in enumerate(experience, 1):
                st.write(f"**Experience {i}:**")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    role = exp.get('role', 'Not specified')
                    company = exp.get('company', 'Not specified')
                    st.write(f"• **Position:** {role}")
                    st.write(f"• **Company:** {company}")
                with col2:
                    period = exp.get('period', 'Not specified')
                    st.write(f"• **Duration:** {period}")
                
                description = exp.get('description', '')
                if description and description.strip():
                    st.write(f"• **Description:** {description}")
                else:
                    st.write("• **Description:** Not provided")
                st.write("")
        else:
            st.write("No work experience provided")
        
        st.divider()
        
        # Education Section - COMPLETE
        st.subheader("🎓 Education")
        education = resume.get('education', [])
        if education:
            for i, edu in enumerate(education, 1):
                st.write(f"**Education {i}:**")
                
                col1, col2 = st.columns(2)
                with col1:
                    degree = edu.get('degree', 'Not specified')
                    institution = edu.get('college_university', 'Not specified')
                    field = edu.get('stream_field', 'Not specified')
                    st.write(f"• **Degree:** {degree}")
                    st.write(f"• **Institution:** {institution}")
                    st.write(f"• **Field of Study:** {field}")
                with col2:
                    period = edu.get('year_period', 'Not specified')
                    grade = edu.get('grade_cgpa_percentage', 'Not specified')
                    st.write(f"• **Period:** {period}")
                    st.write(f"• **Grade/CGPA:** {grade}")
                st.write("")
        else:
            st.write("No education information provided")
        
        st.divider()
        
        # Projects Section - COMPLETE
        st.subheader("🚀 Projects")
        projects = resume.get('projects', [])
        if projects:
            for i, proj in enumerate(projects, 1):
                st.write(f"**Project {i}:**")
                
                col1, col2 = st.columns(2)
                with col1:
                    title = proj.get('project_title', 'Not specified')
                    tech = proj.get('technologies_course_semester', 'Not specified')
                    duration = proj.get('start_end_date', 'Not specified')
                    st.write(f"• **Title:** {title}")
                    st.write(f"• **Technologies:** {tech}")
                    st.write(f"• **Duration:** {duration}")
                with col2:
                    url = proj.get('url', '')
                    team_size = proj.get('team_size', 'Not specified')
                    budget = proj.get('budget_or_size', 'Not specified')
                    
                    if url and url.strip():
                        st.write(f"• **URL:** [Project Link]({url})")
                    else:
                        st.write("• **URL:** Not provided")
                    st.write(f"• **Team Size:** {team_size}")
                    st.write(f"• **Budget/Size:** {budget}")
                
                description = proj.get('description', '')
                if description and description.strip():
                    st.write(f"• **Description:** {description}")
                
                outcome = proj.get('outcome_impact', '')
                if outcome and outcome.strip():
                    st.write(f"• **Outcome/Impact:** {outcome}")
                
                activities = proj.get('key_activities', [])
                if activities:
                    st.write(f"• **Key Activities:** {', '.join(activities)}")
                
                # Certificate info
                certificate = proj.get('certificate', {})
                if certificate and certificate.get('file_name'):
                    st.write(f"• **Certificate:** {certificate.get('file_name')} (Uploaded: {certificate.get('uploaded_at', 'Unknown')})")
                
                st.write("")
        else:
            st.write("No projects provided")
        
        st.divider()
        
        # Certifications Section - COMPLETE
        certifications = resume.get('certifications', [])
        if certifications:
            st.subheader("🏆 Certifications")
            for i, cert in enumerate(certifications, 1):
                if isinstance(cert, str) and cert.strip():
                    st.write(f"{i}. {cert}")
                elif isinstance(cert, dict):
                    cert_name = cert.get('name', cert.get('certification', 'Unnamed Certification'))
                    st.write(f"{i}. {cert_name}")
        else:
            st.write("**🏆 Certifications:** None provided")
        
        # Relevant Coursework Section - COMPLETE
        coursework = resume.get('relevant_coursework', [])
        if coursework:
            st.subheader("📚 Relevant Coursework")
            for i, course in enumerate(coursework, 1):
                if isinstance(course, str) and course.strip():
                    st.write(f"{i}. {course}")
                elif isinstance(course, dict):
                    course_name = course.get('name', course.get('course', 'Unnamed Course'))
                    st.write(f"{i}. {course_name}")
        else:
            st.write("**📚 Relevant Coursework:** None provided")
        
        # Extracurricular & Hobbies Section - COMPLETE
        extracurricular = resume.get('extracurricular_hobbies', [])
        if extracurricular:
            st.subheader("🎯 Extracurricular Activities & Hobbies")
            for i, activity in enumerate(extracurricular, 1):
                if isinstance(activity, str) and activity.strip():
                    st.write(f"{i}. {activity}")
                elif isinstance(activity, dict):
                    activity_name = activity.get('name', activity.get('activity', 'Unnamed Activity'))
                    st.write(f"{i}. {activity_name}")
        else:
            st.write("**🎯 Extracurricular Activities & Hobbies:** None provided")
        
        st.divider()
        
        # File Metadata Section
        st.subheader("📄 File Information")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**File Name:** {resume.get('file_name', 'N/A')}")
        with col2:
            st.write(f"**File Type:** {resume.get('file_type', 'N/A')}")
        with col3:
            st.write(f"**Uploaded By:** {resume.get('uploaded_by', 'N/A')}")
        with col4:
            st.write(f"**Upload Date:** {resume.get('uploaded_at', 'N/A')}")
        
        # Raw Text Preview (Optional but useful for debugging)
        with st.expander("📖 Raw Extracted Text Preview (First 2000 chars)"):
            original_text = resume.get('original_text', '')
            if original_text:
                preview_text = original_text[:2000] + "..." if len(original_text) > 2000 else original_text
                st.text_area("Extracted Text", preview_text, height=300, disabled=True)
            else:
                st.write("No extracted text available")
        
        # Debug: Show raw resume data structure
        with st.expander("🔍 Debug: Raw Resume Data"):
            st.json(resume)


def main_app():
    """Main application interface - FOCUSED ON CORE FEATURES"""
    with st.sidebar:
        st.title("🎯 Resume Screener")
        st.write(f"Welcome, {st.session_state.user_email}")
        
        if st.button("Logout"):
            logout_user()
            st.rerun()
        
        st.divider()
        
        # Simplified navigation - NO QUESTIONS PAGE
        page = st.selectbox(
            "Choose Action", 
            ["Upload Resumes", "Rank & Screen", "My Resumes"]
        )
    
    if page == "Upload Resumes":
        upload_page()
    elif page == "Rank & Screen":
        ranking_page()
    elif page == "My Resumes":
        my_resumes_page()

def main():
    """Main application entry point"""
    if not st.session_state.authenticated:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
