"""
Weather API router — GET /api/weather?lat=..&lon=..

Returns a fully validated WeatherResponse or a clean JSON error.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.schemas.weather import WeatherResponse
from app.services.weather_service import WeatherServiceError, get_forecast

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get(
    "",
    response_model=WeatherResponse,
    summary="Get weather forecast",
    description=(
        "Fetch current conditions plus 48-hour hourly and 7-day daily forecasts "
        "for any latitude/longitude pair. Data is sourced from Open-Meteo (free, "
        "no API key required) and cached in-memory for 10 minutes per coordinate."
    ),
)
async def get_weather(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude (decimal degrees)"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude (decimal degrees)"),
) -> WeatherResponse:
    """
    Returns a WeatherResponse containing:
    - **current**: real-time conditions
    - **hourly**: next 48 hours
    - **daily**: next 7 days
    - **cached**: True if this response was served from the 10-minute cache
    """
    try:
        return await get_forecast(lat, lon)
    except WeatherServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc
