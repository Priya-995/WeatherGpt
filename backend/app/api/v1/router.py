from fastapi import APIRouter
from app.api.v1.endpoints import geocode, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(geocode.router, tags=["geocoding"])
