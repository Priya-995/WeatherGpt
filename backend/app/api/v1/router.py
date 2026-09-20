from fastapi import APIRouter
from app.api.v1.endpoints import geocode, health, imd_alerts

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(geocode.router, tags=["geocoding"])
api_router.include_router(imd_alerts.router, tags=["alerts"])
