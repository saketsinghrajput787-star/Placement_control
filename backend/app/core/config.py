import os
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator

# Compute absolute path to project root placement_tower.db
_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_db_file = os.path.join(_root_dir, "placement_tower.db").replace("\\", "/")
DEFAULT_DB_URL = f"sqlite:///{_db_file}"

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Assisted Placement Control Tower"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    
    # Security / JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-dev-key-for-placement-control-tower-min32chars")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # AI / Groq API
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
        "https://placement-control-tower.vercel.app"
    ]

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
