from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "ai_configured": bool(settings.OPENAI_API_KEY),
        "database": settings.DATABASE_URL.split("://")[0]
    }
