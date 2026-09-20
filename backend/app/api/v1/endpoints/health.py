from datetime import datetime, timezone
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "version": "0.1.0",
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }
