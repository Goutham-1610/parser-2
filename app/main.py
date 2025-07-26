# main.py
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.routers import parser, auth

app = FastAPI()

# Add session middleware with a secret key
app.add_middleware(SessionMiddleware, secret_key="yoursecretkey")

app.include_router(auth.router, prefix="/api")
app.include_router(parser.router, prefix="/api")
