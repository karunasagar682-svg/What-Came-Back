import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "WHAT CAME BACK"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./what_came_back.db")
    
    # OpenAI Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ]
    
    # Configurable Business Thresholds
    AGING_THRESHOLD_DAYS: int = 7
    EXPIRING_WINDOW_THRESHOLD_DAYS: int = 7
    HIGH_VALUE_THRESHOLD: float = 1500.0
    DEFECT_ANOMALY_PERCENTAGE: float = 15.0
    EXCESS_INVENTORY_DAYS: int = 45

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
