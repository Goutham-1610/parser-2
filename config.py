import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GOOGLE_API_KEY: str = os.getenv("GEMINI_API_KEY")
    MONGODB_URI: str = os.getenv("MONGODB_URI")

settings = Settings()
