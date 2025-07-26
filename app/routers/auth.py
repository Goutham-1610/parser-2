# app/routers/auth.py
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from pymongo import MongoClient
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["resume_parser"]
users_collection = db["users"]

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Models
class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# Password hashing helpers
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def hash_password(password):
    return pwd_context.hash(password)

# Routes
@router.post("/register")
def register(user: UserRegister):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered.")
    
    hashed = hash_password(user.password)
    users_collection.insert_one({"email": user.email, "password": hashed})
    return {"message": "User registered successfully."}

@router.post("/login")
def login(user: UserLogin, request: Request):
    db_user = users_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    # Store user email in session
    request.session["user"] = user.email
    return {"message": "Login successful"}

@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}

@router.get("/me")
def get_logged_in_user(request: Request):
    user_email = request.session.get("user")
    if not user_email:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {"email": user_email}
