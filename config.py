# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-123456789")  # Add this line

settings = Settings()
