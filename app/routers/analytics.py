from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from collections import defaultdict, Counter
import asyncio
import json
from bson import ObjectId

from app.db.mongo import collection
from app.dependencies.auth import get_current_user
from config import settings

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

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass

manager = ConnectionManager()

@router.websocket("/ws/analytics")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time analytics updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic updates every 30 seconds
            await asyncio.sleep(30)
            
            # Get latest analytics data
            current_data = await get_real_time_metrics()
            await websocket.send_text(json.dumps({
                "type": "analytics_update",
                "data": current_data,
                "timestamp": datetime.utcnow().isoformat()
            }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def get_real_time_metrics() -> Dict[str, Any]:
    """Get real-time metrics for WebSocket updates"""
    try:
        # Get recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        recent_resumes = list(collection.find({
            "uploaded_at": {"$gte": yesterday.isoformat()}
        }))
        
        return {
            "recent_uploads": len(recent_resumes),
            "total_resumes": collection.count_documents({}),
            "processing_queue": 0,  # Could track pending processing jobs
            "active_users": len(set(r.get("uploaded_by") for r in recent_resumes)),
            "last_update": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/analytics/recruitment-metrics")
async def get_recruitment_metrics(
    days_back: Optional[int] = Query(30, ge=1, le=365),
    user_email: str = Depends(get_current_user),
    skills_filter: Optional[List[str]] = Query(None),
    score_range_min: Optional[int] = Query(0, ge=0, le=100),
    score_range_max: Optional[int] = Query(100, ge=0, le=100),
    experience_levels: Optional[List[str]] = Query(None)
):
    """Get enhanced recruitment metrics with filtering"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    
    # Build dynamic filter query
    match_query = {
        "uploaded_by": user_email,
        "uploaded_at": {
            "$gte": start_date.isoformat(),
            "$lte": end_date.isoformat()
        }
    }
    
    # Apply filters
    if skills_filter:
        match_query["professional_summary.skills"] = {"$in": skills_filter}
    
    if experience_levels:
        exp_ranges = []
        for level in experience_levels:
            if level == "entry":
                exp_ranges.extend([0, 1, 2])
            elif level == "mid":
                exp_ranges.extend([3, 4, 5])
            elif level == "senior":
                exp_ranges.extend([6, 7, 8, 9, 10])
        
        match_query["$expr"] = {"$in": [{"$size": "$experience"}, exp_ranges]}
    
    try:
        # Enhanced pipeline with filtering
        pipeline = [
            {"$match": match_query},
            {
                "$addFields": {
                    "upload_date": {
                        "$dateFromString": {"dateString": "$uploaded_at"}
                    },
                    "experience_count": {"$size": {"$ifNull": ["$experience", []]}},
                    "skills_count": {"$size": {"$ifNull": ["$professional_summary.skills", []]}}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$upload_date"
                        }
                    },
                    "count": {"$sum": 1},
                    "avg_skills": {"$avg": "$skills_count"},
                    "avg_experience": {"$avg": "$experience_count"},
                    "candidates": {"$push": "$personal_information.full_name"}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        daily_stats = list(collection.aggregate(pipeline))
        
        # Get total metrics
        total_resumes = collection.count_documents({"uploaded_by": user_email})
        filtered_count = sum(stat["count"] for stat in daily_stats)
        
        return {
            "total_resumes": total_resumes,
            "filtered_resumes": filtered_count,
            "resumes_this_period": filtered_count,
            "daily_uploads": daily_stats,
            "average_skills_per_resume": sum(stat.get("avg_skills", 0) for stat in daily_stats) / len(daily_stats) if daily_stats else 0,
            "average_experience_per_resume": sum(stat.get("avg_experience", 0) for stat in daily_stats) / len(daily_stats) if daily_stats else 0,
            "filters_applied": {
                "skills": skills_filter or [],
                "score_range": [score_range_min, score_range_max],
                "experience_levels": experience_levels or [],
                "date_range": [start_date.isoformat(), end_date.isoformat()]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")

@router.get("/analytics/skills-analysis")
async def get_skills_analysis(
    user_email: str = Depends(get_current_user),
    top_n: Optional[int] = Query(20, ge=5, le=100),
    category_filter: Optional[str] = Query(None),
    min_frequency: Optional[int] = Query(1, ge=1)
):
    """Enhanced skills analysis with filtering and categorization"""
    
    try:
        # Skills categorization (you can expand this)
        skill_categories = {
            "programming": ["python", "javascript", "java", "c++", "c#", "php", "ruby", "go", "rust"],
            "web": ["html", "css", "react", "angular", "vue", "nodejs", "express", "django", "flask"],
            "database": ["mysql", "postgresql", "mongodb", "redis", "elasticsearch", "sqlite"],
            "cloud": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform"],
            "ml_ai": ["machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn", "nlp"],
            "mobile": ["android", "ios", "react native", "flutter", "xamarin"],
            "tools": ["git", "jenkins", "jira", "confluence", "slack", "figma"]
        }
        
        pipeline = [
            {"$match": {"uploaded_by": user_email}},
            {"$unwind": "$professional_summary.skills"},
            {
                "$group": {
                    "_id": {"$toLower": "$professional_summary.skills"},
                    "count": {"$sum": 1},
                    "candidates": {"$addToSet": "$personal_information.full_name"}
                }
            },
            {"$match": {"count": {"$gte": min_frequency}}},
            {"$sort": {"count": -1}},
            {"$limit": top_n}
        ]
        
        skills_data = list(collection.aggregate(pipeline))
        
        # Categorize skills if filter is applied
        if category_filter and category_filter in skill_categories:
            category_skills = skill_categories[category_filter]
            skills_data = [
                skill for skill in skills_data 
                if any(cat_skill in skill["_id"] for cat_skill in category_skills)
            ]
        
        # Calculate trends (compare with previous period)
        previous_period_start = datetime.utcnow() - timedelta(days=60)
        current_period_start = datetime.utcnow() - timedelta(days=30)
        
        trend_pipeline = [
            {
                "$match": {
                    "uploaded_by": user_email,
                    "uploaded_at": {
                        "$gte": previous_period_start.isoformat(),
                        "$lt": current_period_start.isoformat()
                    }
                }
            },
            {"$unwind": "$professional_summary.skills"},
            {
                "$group": {
                    "_id": {"$toLower": "$professional_summary.skills"},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        previous_skills = {skill["_id"]: skill["count"] for skill in collection.aggregate(trend_pipeline)}
        
        # Add trend information
        for skill in skills_data:
            previous_count = previous_skills.get(skill["_id"], 0)
            current_count = skill["count"]
            
            if previous_count > 0:
                trend = ((current_count - previous_count) / previous_count) * 100
                skill["trend"] = round(trend, 1)
            else:
                skill["trend"] = 100 if current_count > 0 else 0
        
        return {
            "top_skills": [
                {
                    "skill": item["_id"],
                    "count": item["count"],
                    "candidates": item["candidates"],
                    "trend": item.get("trend", 0)
                } for item in skills_data
            ],
            "total_unique_skills": len(skills_data),
            "category_filter": category_filter,
            "available_categories": list(skill_categories.keys()),
            "filters_applied": {
                "top_n": top_n,
                "category": category_filter,
                "min_frequency": min_frequency
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skills analysis error: {str(e)}")

@router.get("/analytics/ranking-performance")
async def get_ranking_performance(
    user_email: str = Depends(get_current_user),
    job_description_filter: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """Enhanced ranking performance with filtering"""
    
    try:
        match_query = {"uploaded_by": user_email}
        
        # Apply date filters
        if date_from or date_to:
            date_filter = {}
            if date_from:
                date_filter["$gte"] = date_from
            if date_to:
                date_filter["$lte"] = date_to
            match_query["uploaded_at"] = date_filter
        
        # Get all resumes for score analysis
        resumes = list(collection.find(match_query))
        
        if not resumes:
            return {
                "score_distribution": [],
                "high_performers": 0,
                "average_score": 0,
                "total_ranked": 0,
                "performance_trends": [],
                "filters_applied": {
                    "job_description": job_description_filter,
                    "date_range": [date_from, date_to]
                }
            }
        
        # Calculate score distribution
        score_buckets = defaultdict(int)
        total_score = 0
        scored_resumes = 0
        
        for resume in resumes:
            # Scoring logic based on resume content
            skills_count = len(resume.get("professional_summary", {}).get("skills", []))
            experience_count = len(resume.get("experience", []))
            education_count = len(resume.get("education", []))
            
            # Scoring algorithm
            score = min(100, (skills_count * 2) + (experience_count * 10) + (education_count * 5))
            
            bucket = (score // 20) * 20  # Group into 20-point buckets
            score_buckets[bucket] += 1
            total_score += score
            scored_resumes += 1
        
        average_score = total_score / scored_resumes if scored_resumes > 0 else 0
        high_performers = sum(count for score, count in score_buckets.items() if score >= 80)
        
        # Performance trends over time
        performance_trends = []
        for i in range(7):  # Last 7 days
            date = datetime.utcnow() - timedelta(days=i)
            day_resumes = [r for r in resumes if r.get("uploaded_at", "").startswith(date.strftime("%Y-%m-%d"))]
            day_score = sum(min(100, (len(r.get("professional_summary", {}).get("skills", [])) * 2) + 
                              (len(r.get("experience", [])) * 10)) for r in day_resumes)
            avg_day_score = day_score / len(day_resumes) if day_resumes else 0
            
            performance_trends.append({
                "date": date.strftime("%Y-%m-%d"),
                "average_score": round(avg_day_score, 1),
                "resume_count": len(day_resumes)
            })
        
        return {
            "score_distribution": [
                {"score_range": f"{score}-{score+19}", "count": count}
                for score, count in sorted(score_buckets.items())
            ],
            "high_performers": high_performers,
            "average_score": round(average_score, 1),
            "total_ranked": scored_resumes,
            "performance_trends": list(reversed(performance_trends)),
            "score_breakdown": {
                "excellent": sum(count for score, count in score_buckets.items() if score >= 80),
                "good": sum(count for score, count in score_buckets.items() if 60 <= score < 80),
                "average": sum(count for score, count in score_buckets.items() if 40 <= score < 60),
                "below_average": sum(count for score, count in score_buckets.items() if score < 40)
            },
            "filters_applied": {
                "job_description": job_description_filter,
                "date_range": [date_from, date_to]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ranking performance error: {str(e)}")

@router.get("/analytics/real-time-dashboard")
async def get_real_time_dashboard(
    user_email: str = Depends(get_current_user),
    refresh_interval: Optional[int] = Query(30, ge=10, le=300)
):
    """Get real-time dashboard data"""
    
    try:
        now = datetime.utcnow()
        
        # Last 24 hours activity
        last_24h = now - timedelta(hours=24)
        recent_activity = list(collection.find({
            "uploaded_by": user_email,
            "uploaded_at": {"$gte": last_24h.isoformat()}
        }))
        
        # Processing queue simulation (in real app, this would track actual processing jobs)
        processing_queue = 0
        
        # Active sessions simulation
        active_sessions = 1  # Current user
        
        # System health metrics
        system_health = {
            "api_response_time": "120ms",
            "database_status": "healthy",
            "ai_service_status": "operational",
            "storage_usage": "78%"
        }
        
        # Recent uploads with details
        recent_uploads = []
        for resume in recent_activity[-10:]:  # Last 10 uploads
            upload_time = datetime.fromisoformat(resume.get("uploaded_at", now.isoformat()))
            time_ago = now - upload_time
            
            recent_uploads.append({
                "candidate_name": resume.get("personal_information", {}).get("full_name", "Unknown"),
                "uploaded_at": upload_time.isoformat(),
                "time_ago": f"{int(time_ago.total_seconds() // 3600)}h {int((time_ago.total_seconds() % 3600) // 60)}m ago",
                "file_type": resume.get("file_type", "unknown"),
                "skills_count": len(resume.get("professional_summary", {}).get("skills", [])),
                "processing_status": "completed"
            })
        
        return {
            "timestamp": now.isoformat(),
            "refresh_interval": refresh_interval,
            "activity_summary": {
                "uploads_last_24h": len(recent_activity),
                "processing_queue": processing_queue,
                "active_sessions": active_sessions,
                "total_resumes": collection.count_documents({"uploaded_by": user_email})
            },
            "system_health": system_health,
            "recent_uploads": recent_uploads,
            "hourly_activity": [
                {
                    "hour": (now - timedelta(hours=i)).strftime("%H:00"),
                    "uploads": len([r for r in recent_activity 
                                  if datetime.fromisoformat(r.get("uploaded_at", "")).hour == (now - timedelta(hours=i)).hour])
                } for i in range(24)
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Real-time dashboard error: {str(e)}")

@router.get("/analytics/advanced-filters")
async def get_filter_options(user_email: str = Depends(get_current_user)):
    """Get available filter options for advanced filtering"""
    
    try:
        # Get all unique values for filtering
        pipeline = [
            {"$match": {"uploaded_by": user_email}},
            {
                "$group": {
                    "_id": None,
                    "skills": {"$addToSet": "$professional_summary.skills"},
                    "locations": {"$addToSet": "$personal_information.location"},
                    "education_degrees": {"$addToSet": "$education.degree"},
                    "companies": {"$addToSet": "$experience.company"},
                    "date_range": {
                        "$push": {
                            "$dateFromString": {"dateString": "$uploaded_at"}
                        }
                    }
                }
            }
        ]
        
        result = list(collection.aggregate(pipeline))
        
        if not result:
            return {
                "skills": [],
                "locations": [],
                "education_degrees": [],
                "companies": [],
                "date_range": {"min": None, "max": None},
                "experience_levels": ["entry", "mid", "senior"],
                "score_ranges": [
                    {"label": "Excellent (80-100)", "min": 80, "max": 100},
                    {"label": "Good (60-79)", "min": 60, "max": 79},
                    {"label": "Average (40-59)", "min": 40, "max": 59},
                    {"label": "Below Average (0-39)", "min": 0, "max": 39}
                ]
            }
        
        data = result[0]
        
        # Flatten nested arrays and remove None values
        skills = []
        for skill_list in data.get("skills", []):
            if isinstance(skill_list, list):
                skills.extend([s for s in skill_list if s])
            elif skill_list:
                skills.append(skill_list)
        
        locations = [loc for loc in data.get("locations", []) if loc]
        degrees = []
        for deg_list in data.get("education_degrees", []):
            if isinstance(deg_list, list):
                degrees.extend([d for d in deg_list if d])
            elif deg_list:
                degrees.append(deg_list)
        
        companies = []
        for comp_list in data.get("companies", []):
            if isinstance(comp_list, list):
                companies.extend([c for c in comp_list if c])
            elif comp_list:
                companies.append(comp_list)
        
        dates = [d for d in data.get("date_range", []) if d]
        date_range = {
            "min": min(dates).isoformat() if dates else None,
            "max": max(dates).isoformat() if dates else None
        }
        
        return {
            "skills": sorted(list(set(skills)))[:50],  # Top 50 skills
            "locations": sorted(list(set(locations))),
            "education_degrees": sorted(list(set(degrees))),
            "companies": sorted(list(set(companies)))[:30],  # Top 30 companies
            "date_range": date_range,
            "experience_levels": [
                {"label": "Entry Level (0-2 years)", "value": "entry"},
                {"label": "Mid Level (3-5 years)", "value": "mid"},
                {"label": "Senior Level (6+ years)", "value": "senior"}
            ],
            "score_ranges": [
                {"label": "Excellent (80-100)", "min": 80, "max": 100},
                {"label": "Good (60-79)", "min": 60, "max": 79},
                {"label": "Average (40-59)", "min": 40, "max": 59},
                {"label": "Below Average (0-39)", "min": 0, "max": 39}
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Filter options error: {str(e)}")

@router.get("/analytics/filtered-resumes")
async def get_filtered_resumes(
    user_email: str = Depends(get_current_user),
    skills_filter: Optional[List[str]] = Query(None),
    locations_filter: Optional[List[str]] = Query(None),
    education_filter: Optional[List[str]] = Query(None),
    experience_levels: Optional[List[str]] = Query(None),
    score_min: Optional[int] = Query(0),
    score_max: Optional[int] = Query(100),
    limit: Optional[int] = Query(50)
):
    """Get resumes that match the applied filters"""
    
    try:
        # Build MongoDB query
        match_query = {"uploaded_by": user_email}
        
        # Apply filters
        if skills_filter:
            match_query["professional_summary.skills"] = {"$in": skills_filter}
        
        if locations_filter:
            match_query["personal_information.location"] = {"$in": locations_filter}
        
        if education_filter:
            match_query["education.degree"] = {"$in": education_filter}
        
        if experience_levels:
            exp_ranges = []
            for level in experience_levels:
                if level == "entry":
                    exp_ranges.extend([0, 1, 2])
                elif level == "mid":
                    exp_ranges.extend([3, 4, 5])
                elif level == "senior":
                    exp_ranges.extend([6, 7, 8, 9, 10])
            
            if exp_ranges:
                match_query["$expr"] = {"$in": [{"$size": {"$ifNull": ["$experience", []]}}, exp_ranges]}
        
        # Aggregation pipeline with score calculation
        pipeline = [
            {"$match": match_query},
            {
                "$addFields": {
                    "calculated_score": {
                        "$min": [
                            100,
                            {
                                "$add": [
                                    {"$multiply": [{"$size": {"$ifNull": ["$professional_summary.skills", []]}}, 2]},
                                    {"$multiply": [{"$size": {"$ifNull": ["$experience", []]}}, 10]},
                                    {"$multiply": [{"$size": {"$ifNull": ["$education", []]}}, 5]}
                                ]
                            }
                        ]
                    }
                }
            },
            {
                "$match": {
                    "calculated_score": {"$gte": score_min, "$lte": score_max}
                }
            },
            {"$sort": {"calculated_score": -1}},
            {"$limit": limit}
        ]
        
        filtered_resumes = list(collection.aggregate(pipeline))
        total_matches = len(filtered_resumes)
        
        return {
            "filtered_resumes": convert_objectid(filtered_resumes),
            "total_matches": total_matches,
            "applied_filters": {
                "skills": skills_filter or [],
                "locations": locations_filter or [],
                "education": education_filter or [],
                "experience_levels": experience_levels or [],
                "score_range": [score_min, score_max]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Filtered resumes error: {str(e)}")
