import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import time

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

# Custom CSS (Fixed HTML encoding)
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
    .live-indicator {
        background-color: #ff4444;
        border-radius: 50%;
        width: 10px;
        height: 10px;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
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
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type
                        )
                    }
                    
                    response = st.session_state.session.post(
                        f"{API_BASE_URL}/parse-resume/", 
                        files=files
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
                    
                    # Score distribution chart with unique key
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
                        st.plotly_chart(fig, use_container_width=True, key="ranking_score_distribution")
                    
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

def analytics_page():
    """Enhanced Real-Time HR Analytics Dashboard with Real Data"""
    st.title("📊 Real-Time HR Analytics Dashboard")
    st.write("Live insights using actual resume data from your database")
    
    # Real-time controls
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        st.markdown('<div class="live-indicator"></div> **Live Analytics - Real Data**', unsafe_allow_html=True)
    
    with col2:
        auto_refresh = st.checkbox("🔄 Auto Refresh", value=False)
    
    with col3:
        refresh_interval = st.selectbox("Refresh Rate (s)", [10, 30, 60, 120], index=1)
    
    with col4:
        if st.button("🔄 Refresh Now"):
            st.rerun()
    
    # Advanced Filters Section
    with st.expander("🎛️ Advanced Filters", expanded=False):
        render_advanced_filters()
    
    # Real-time dashboard
    if auto_refresh:
        placeholder = st.empty()
        
        for i in range(0, refresh_interval + 1):
            with placeholder.container():
                render_analytics_content()
                
                if i < refresh_interval:
                    st.info(f"Next refresh in {refresh_interval - i} seconds...")
                    time.sleep(1)
                else:
                    st.success("Dashboard updated!")
                    st.rerun()
    else:
        render_analytics_content()
    
    # Real Filtered Resumes Section
    st.divider()
    render_filtered_resumes()

def render_advanced_filters():
    """Advanced filtering interface with real filter options and debugging"""
    try:
        # Get REAL filter options from your API
        filter_response = st.session_state.session.get(f"{API_BASE_URL}/analytics/advanced-filters")
        
        if filter_response.status_code == 200:
            filter_options = filter_response.json()
            st.success("✅ Using real filter options from database")
            
            # Debug: Show what we received
            with st.expander("🔍 Debug - API Response", expanded=False):
                st.json(filter_options)
        else:
            st.warning("⚠️ API failed, using default options")
            filter_options = {
                'skills': ['Python', 'JavaScript', 'React', 'Machine Learning'],
                'locations': ['Bangalore', 'Mumbai', 'Delhi'],
                'education_degrees': ['Bachelor of Technology', 'Master of Science'],
                'date_range': {'min': '2025-07-26', 'max': '2025-07-26'}
            }
        
        # Safely extract filter data
        skills = filter_options.get('skills', [])
        locations = filter_options.get('locations', [])
        degrees = filter_options.get('education_degrees', [])
        
        st.write(f"**Found:** {len(skills)} skills, {len(locations)} locations, {len(degrees)} degrees")
        
        # Display filter columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**📊 Data Filters**")
            
            # Safe date range handling
            date_range_info = filter_options.get('date_range', {})
            if date_range_info and date_range_info.get('min'):
                try:
                    max_date = datetime.fromisoformat(date_range_info['max']).date()
                    st.info(f"📅 Data available for: {max_date}")
                except:
                    st.info("📅 No date range available")
            
            # Score range filter (always available)
            score_range = st.slider(
                "Score Range",
                min_value=0,
                max_value=100,
                value=(60, 100),
                step=5,
                key="analytics_score_range_filter"
            )
        
        with col2:
            st.write("**🛠️ Skills & Experience**")
            
            # Skills filter
            if skills and len(skills) > 0:
                safe_skills = [str(skill) for skill in skills if skill][:20]
                selected_skills = st.multiselect(
                    "Filter by Skills",
                    options=safe_skills,
                    default=[],
                    key="analytics_skills_filter"
                )
            else:
                st.info("No skills data available")
                selected_skills = []
            
            # Experience level filter (always available)
            experience_levels = st.multiselect(
                "Experience Level",
                options=["entry", "mid", "senior"],
                default=["entry", "mid", "senior"],
                key="analytics_experience_filter"
            )
        
        with col3:
            st.write("**🎓 Background Filters**")
            
            # Location filter
            if locations and len(locations) > 0:
                safe_locations = [str(loc) for loc in locations if loc][:15]
                selected_locations = st.multiselect(
                    "Filter by Location",
                    options=safe_locations,
                    default=[],
                    key="analytics_locations_filter"
                )
            else:
                st.info("No location data available")
                selected_locations = []
            
            # Education filter
            if degrees and len(degrees) > 0:
                safe_degrees = [str(deg) for deg in degrees if deg][:10]
                selected_degrees = st.multiselect(
                    "Filter by Education",
                    options=safe_degrees,
                    default=[],
                    key="analytics_education_filter"
                )
            else:
                st.info("No education data available")
                selected_degrees = []
        
        # Store filters in session state
        st.session_state.analytics_filters = {
            'skills': selected_skills,
            'experience_levels': experience_levels,
            'score_range': score_range,
            'locations': selected_locations,
            'degrees': selected_degrees
        }
        
        # Apply filters button
        if st.button("📊 Apply Filters", key="apply_analytics_filters"):
            st.success("Filters applied! Dashboard will update with filtered data.")
            st.rerun()
        
    except Exception as e:
        st.error(f"Error loading filter options: {str(e)}")

def render_analytics_content():
    """Complete analytics content with REAL data from APIs"""
    
    filters = getattr(st.session_state, 'analytics_filters', {})
    
    try:
        # Show loading state
        st.write("🔄 Loading analytics data from real database...")
        
        # Prepare API parameters for REAL data
        params = {
            'skills_filter': filters.get('skills', []),
            'score_range_min': filters.get('score_range', [0, 100])[0],
            'score_range_max': filters.get('score_range', [0, 100])[1],
            'experience_levels': filters.get('experience_levels', [])
        }
        params = {k: v for k, v in params.items() if v}
        
        # Make REAL API calls to analytics endpoints
        with st.spinner("📊 Fetching data from backend..."):
            recruitment_response = st.session_state.session.get(f"{API_BASE_URL}/analytics/recruitment-metrics", params=params)
            skills_response = st.session_state.session.get(f"{API_BASE_URL}/analytics/skills-analysis")
            ranking_response = st.session_state.session.get(f"{API_BASE_URL}/analytics/ranking-performance")
            dashboard_response = st.session_state.session.get(f"{API_BASE_URL}/analytics/real-time-dashboard")
        
        # Debug: Show response status codes
        st.write("**🔍 API Response Status:**")
        st.write(f"- Recruitment metrics: {recruitment_response.status_code}")
        st.write(f"- Skills analysis: {skills_response.status_code}")
        st.write(f"- Ranking performance: {ranking_response.status_code}")
        st.write(f"- Real-time dashboard: {dashboard_response.status_code}")
        
        # Check if all calls succeeded
        if all(r.status_code == 200 for r in [recruitment_response, skills_response, ranking_response, dashboard_response]):
            # Parse REAL data from APIs
            recruitment_data = recruitment_response.json()
            skills_data = skills_response.json()
            ranking_data = ranking_response.json()
            dashboard_data = dashboard_response.json()
            
            st.success("✅ Successfully loaded real-time analytics data")
            
            # Show data counts
            recent_uploads = dashboard_data.get('recent_uploads', [])
            top_skills = skills_data.get('top_skills', [])
            
            st.write(f"**📊 Data Summary:**")
            st.write(f"- Recent uploads: {len(recent_uploads)}")
            st.write(f"- Top skills found: {len(top_skills)}")
            st.write(f"- Total resumes: {recruitment_data.get('total_resumes', 0)}")
            
            # Debug: Show data structure (optional)
            with st.expander("🔍 Debug - Raw Data", expanded=False):
                st.write("**Dashboard Data:**")
                st.json(dashboard_data)
            
            # Try to render components with real data
            if recruitment_data.get('total_resumes', 0) > 0:
                render_real_time_status(dashboard_data)
                render_enhanced_kpi_cards(recruitment_data, ranking_data, dashboard_data)
                render_real_time_charts(recruitment_data, skills_data, ranking_data, dashboard_data)
                render_live_activity_feed(dashboard_data)
            else:
                st.warning("⚠️ No resume data available. Upload some resumes first to see analytics!")
                st.info("👉 Go to 'Upload Resumes' to add data to your database")
                
        else:
            st.error("❌ Some API calls failed")
            # Show specific error details
            responses = [recruitment_response, skills_response, ranking_response, dashboard_response]
            endpoint_names = ["recruitment-metrics", "skills-analysis", "ranking-performance", "real-time-dashboard"]
            
            for i, response in enumerate(responses):
                if response.status_code != 200:
                    st.write(f"- **{endpoint_names[i]}**: {response.status_code}")
                    try:
                        error_detail = response.json().get('detail', 'Unknown error')
                        st.write(f"  Error: {error_detail}")
                    except:
                        st.write(f"  Raw error: {response.text}")
        
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to analytics API")
        st.write("**Troubleshooting Steps:**")
        st.write("1. Make sure FastAPI server is running: `uvicorn app.main:app --reload --port 8000`")
        st.write("2. Check if analytics router is included in main.py")
        st.write("3. Verify API_BASE_URL is correct")
        st.write("4. Check if MongoDB is running and accessible")
    except Exception as e:
        st.error(f"❌ Error loading real-time analytics: {str(e)}")
        st.write("**Full error details:**")
        st.code(str(e))

def render_real_time_status(dashboard_data):
    """Render real-time system status with actual data"""
    activity = dashboard_data.get('activity_summary', {})
    health = dashboard_data.get('system_health', {})
    
    st.subheader("🔴 System Status - Real Data")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🟢 System Status", 
            "ACTIVE",
            delta="Real-time"
        )
    
    with col2:
        st.metric(
            "⚡ Processing Queue", 
            activity.get('processing_queue', 0),
            delta=f"{activity.get('uploads_last_24h', 0)} in 24h"
        )
    
    with col3:
        st.metric(
            "👥 Active Sessions", 
            activity.get('active_sessions', 1),
            delta="Current"
        )
    
    with col4:
        st.metric(
            "🔧 API Response", 
            health.get('api_response_time', 'N/A'),
            delta=health.get('database_status', 'Unknown')
        )

def render_enhanced_kpi_cards(recruitment_data, ranking_data, dashboard_data):
    """Render enhanced KPI cards with real filter information"""
    
    st.subheader("📊 Key Performance Indicators - Real Data")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = recruitment_data.get('total_resumes', 0)
        filtered = recruitment_data.get('filtered_resumes', 0)
        st.metric(
            "📤 Total Resumes", 
            f"{filtered:,}",
            delta=f"of {total:,} total" if filtered != total else None,
            help="Filtered results based on current criteria"
        )
    
    with col2:
        avg_score = ranking_data.get('average_score', 0)
        st.metric(
            "⭐ Average Score", 
            f"{avg_score:.1f}%",
            delta=f"{avg_score-70:.1f}%" if avg_score > 70 else f"{70-avg_score:.1f}%",
            delta_color="normal" if avg_score > 70 else "inverse"
        )
    
    with col3:
        high_performers = ranking_data.get('high_performers', 0)
        total_ranked = ranking_data.get('total_ranked', 1)
        high_performer_rate = (high_performers / total_ranked) * 100 if total_ranked > 0 else 0
        st.metric(
            "🏆 High Performers", 
            f"{high_performer_rate:.1f}%",
            delta=f"{high_performers} candidates"
        )
    
    with col4:
        uploads_24h = dashboard_data.get('activity_summary', {}).get('uploads_last_24h', 0)
        st.metric(
            "📈 Activity (24h)", 
            f"{uploads_24h}",
            delta="uploads"
        )

def render_real_time_charts(recruitment_data, skills_data, ranking_data, dashboard_data):
    """Render real-time interactive charts with unique keys and real data"""
    
    # Hourly activity chart
    st.subheader("📈 Real-Time Activity")
    hourly_data = dashboard_data.get('hourly_activity', [])
    if hourly_data and len(hourly_data) > 0:
        df_hourly = pd.DataFrame(hourly_data)
        
        fig_hourly = px.bar(
            df_hourly,
            x='hour',
            y='uploads',
            title="Uploads by Hour (Last 24h) - Real Data",
            color='uploads',
            color_continuous_scale='blues'
        )
        fig_hourly.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_hourly, use_container_width=True, key="hourly_activity_chart")
    else:
        st.info("No hourly activity data available yet")
    
    # Performance trends and skills charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Performance Trends")
        trends = ranking_data.get('performance_trends', [])
        if trends and len(trends) > 0:
            df_trends = pd.DataFrame(trends)
            
            fig_trends = px.line(
                df_trends,
                x='date',
                y='average_score',
                title="Average Score Trend (7 days) - Real Data",
                markers=True
            )
            fig_trends.update_layout(height=400)
            st.plotly_chart(fig_trends, use_container_width=True, key="performance_trends_chart")
        else:
            st.info("No performance trend data available yet")
    
    with col2:
        st.subheader("🛠️ Skills Trends")
        skills_with_trends = skills_data.get('top_skills', [])
        if skills_with_trends and len(skills_with_trends) > 0:
            skills_df = pd.DataFrame(skills_with_trends)
            
            fig_skills = px.bar(
                skills_df,
                x='count',
                y='skill',
                orientation='h',
                title="Top Skills with Growth - Real Data",
                color='trend',
                color_continuous_scale='RdYlGn',
                hover_data=['trend']
            )
            fig_skills.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_skills, use_container_width=True, key="skills_trends_chart")
        else:
            st.info("No skills trend data available yet")

def render_live_activity_feed(dashboard_data):
    """Render live activity feed with REAL data"""
    st.subheader("🔴 Live Activity Feed - Real Data")
    
    recent_uploads = dashboard_data.get('recent_uploads', [])
    
    if recent_uploads and len(recent_uploads) > 0:
        st.write(f"**Showing {len(recent_uploads)} recent uploads:**")
        
        for upload in recent_uploads:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.write(f"**{upload.get('candidate_name', 'Unknown')}**")
            
            with col2:
                st.write(f"⏱️ {upload.get('time_ago', 'Unknown')}")
            
            with col3:
                file_type = upload.get('file_type', 'unknown').upper()
                st.write(f"📄 {file_type}")
            
            with col4:
                status = upload.get('processing_status', 'unknown')
                color = "🟢" if status == "completed" else "🟡" if status == "processing" else "🔴"
                st.write(f"{color} {status.title()}")
    else:
        st.info("No recent activity to display. Upload some resumes to see live activity!")
    
    # Add timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def render_filtered_resumes():
    """Display resumes that match the current filters using REAL API"""
    
    filters = getattr(st.session_state, 'analytics_filters', {})
    
    if not any(filters.values()):
        st.info("🎛️ Apply filters above to see filtered resume results")
        return
    
    st.subheader("📋 Filtered Resume Results - Real Data")
    
    try:
        # Prepare API parameters for real filtering
        params = {
            'skills_filter': filters.get('skills', []),
            'locations_filter': filters.get('locations', []),
            'education_filter': filters.get('degrees', []),
            'experience_levels': filters.get('experience_levels', []),
            'score_min': filters.get('score_range', [0, 100])[0],
            'score_max': filters.get('score_range', [0, 100])[1],
            'limit': 20
        }
        
        # Remove empty parameters
        params = {k: v for k, v in params.items() if v}
        
        # Make API call to get REAL filtered resumes
        with st.spinner("🔍 Filtering resumes from database..."):
            response = st.session_state.session.get(f"{API_BASE_URL}/analytics/filtered-resumes", params=params)
            
            if response.status_code == 200:
                result = response.json()
                filtered_resumes = result.get('filtered_resumes', [])
                total_matches = result.get('total_matches', 0)
                
                if filtered_resumes:
                    st.success(f"✅ Found {total_matches} real resumes matching your filters")
                    
                    # Display summary with REAL data
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📊 Total Matches", total_matches)
                    with col2:
                        avg_score = sum(r.get('calculated_score', 0) for r in filtered_resumes) / len(filtered_resumes)
                        st.metric("📈 Average Score", f"{avg_score:.1f}%")
                    with col3:
                        high_quality = sum(1 for r in filtered_resumes if r.get('calculated_score', 0) >= 80)
                        st.metric("⭐ High Quality", f"{high_quality}/{total_matches}")
                    
                    st.divider()
                    
                    # Display REAL filtered resumes
                    for i, resume in enumerate(filtered_resumes, 1):
                        display_real_resume_card(resume, i)
                        
                else:
                    st.warning("⚠️ No resumes match your current filters. Try adjusting the filter criteria.")
                    
            else:
                st.error(f"❌ Failed to fetch filtered resumes. Status: {response.status_code}")
                
    except Exception as e:
        st.error(f"Error filtering resumes: {str(e)}")

def display_real_resume_card(resume, position):
    """Display a real resume card with actual data from database"""
    personal_info = resume.get('personal_information', {})
    prof_summary = resume.get('professional_summary', {})
    
    # Extract REAL data from database
    name = personal_info.get('full_name', 'Unknown')
    email = personal_info.get('email', '')
    location = personal_info.get('location', '')
    skills = prof_summary.get('skills', [])[:8]
    experience_count = len(resume.get('experience', []))
    education = resume.get('education', [{}])[0].get('degree', '') if resume.get('education') else ''
    calculated_score = resume.get('calculated_score', 0)
    
    # Color coding based on actual calculated score
    if calculated_score >= 80:
        score_color = "#28a745"
        badge = "🥇"
    elif calculated_score >= 70:
        score_color = "#17a2b8"
        badge = "🥈"
    elif calculated_score >= 60:
        score_color = "#ffc107"
        badge = "🥉"
    else:
        score_color = "#dc3545"
        badge = "📋"
    
    with st.container():
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown(f"""
            <div style="border-left: 4px solid {score_color}; padding-left: 15px; margin: 10px 0;">
                <h4>{badge} #{position} - {name}</h4>
                <p><strong>📧 Email:</strong> {email}</p>
                <p><strong>📍 Location:</strong> {location}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if skills:
                st.write("**🛠️ Real Skills:**")
                skills_text = " • ".join(skills)
                st.write(skills_text)
            
            st.write(f"**📈 Experience:** {experience_count} positions")
            if education:
                st.write(f"**🎓 Education:** {education}")
        
        with col3:
            st.metric("Real Score", f"{calculated_score}%")
            
            if st.button(f"📋 View Full Resume", key=f"view_real_resume_{position}"):
                st.session_state.selected_resume_id = resume.get('_id')
                st.success(f"✅ Selected {name} - showing real database record")
        
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
        # Personal Information Section
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
        
        # Professional Summary Section
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
            # Enhanced skills display with better styling
            skills_html = ""
            for skill in skills:
                skills_html += f'''
                <span style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; 
                    padding: 4px 12px; 
                    margin: 2px; 
                    border-radius: 16px; 
                    font-size: 12px; 
                    font-weight: 500;
                    display: inline-block;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">{skill}</span> '''
            st.markdown(skills_html, unsafe_allow_html=True)
        else:
            st.write("**Skills:** Not provided")

def main_app():
    """Main application interface with Real-Time Analytics Dashboard"""
    with st.sidebar:
        st.title("🎯 Resume Screener")
        st.write(f"Welcome, {st.session_state.user_email}")
        
        if st.button("Logout"):
            logout_user()
            st.rerun()
        
        st.divider()
        
        # Updated navigation with Real-Time Analytics
        page = st.selectbox(
            "Choose Action", 
            ["Upload Resumes", "Rank & Screen", "My Resumes", "📊 Real-Time Analytics"]
        )
    
    if page == "Upload Resumes":
        upload_page()
    elif page == "Rank & Screen":
        ranking_page()
    elif page == "My Resumes":
        my_resumes_page()
    elif page == "📊 Real-Time Analytics":
        analytics_page()

def main():
    """Main application entry point"""
    if not st.session_state.authenticated:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
