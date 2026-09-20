from fastapi import APIRouter, Query

from app.schemas.geo import GeocodeResponse
from app.services.geocoding import search_places

router = APIRouter()


@router.get("/geocode", response_model=GeocodeResponse)
async def geocode_endpoint(
    q: str = Query(..., min_length=2, max_length=100, description="Location search query (minimum 2 chars)"),
    limit: int = Query(5, ge=1, le=10, description="Max results to return (1-10)"),
    country: str = Query("IN", description="ISO alpha-2 country code filter (empty string disables filter)"),
    lang: str = Query("en", pattern="^(en|hi)$", description="Language for results (en or hi)"),
):
    places = await search_places(query=q, limit=limit, country=country, language=lang)
    return GeocodeResponse(query=q, count=len(places), results=places)
