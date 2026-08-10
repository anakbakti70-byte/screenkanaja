import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend root (3 levels up from this file: app/core/config.py)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    PROJECT_NAME: str = "Stock Trading Scanner"
    
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_DATABASE_PASSWORD: str = os.getenv("SUPABASE_DATABASE_PASSWORD", "")
    SUPABASE_URI_SESSIONPOOLER: str = os.getenv("SUPABASE_URI_SESSIONPOOLER", "")

    GROQ_API: str = os.getenv("GROQ_API", "")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()
