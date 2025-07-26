from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.routers import auth, parser 
from app.routers import analytics 
from config import settings


app = FastAPI(
    title="LLM Resume Screener API",
    description="AI-powered resume screening and ranking system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY  # Make sure you have this in your config
)

# Include routers with /api prefix
app.include_router(auth.router, prefix="/api", tags=["authentication"])
app.include_router(parser.router, prefix="/api", tags=["resume-processing"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])

@app.get("/")
async def root():
    return {"message": "LLM Resume Screener API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is working correctly"}

# Debug endpoint to see all routes
@app.get("/debug/routes")
async def list_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, 'name', 'N/A')
            })
    return {"routes": routes}

@app.on_event("startup")
async def startup_event():
    print("Available routes:")
    for route in app.routes:
        if hasattr(route, 'methods'):
            print(f"{route.methods} {route.path}")
