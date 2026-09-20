"""
Location / geocoding API router — GET /api/location/search?q=<place>

Returns all matching Location objects for the query string.
No-match → empty list (count: 0).  Multiple matches → full list (no guessing).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.location import LocationSearchResponse
from app.services.location_service import GeocodingServiceError, geocode

router = APIRouter(prefix="/api/location", tags=["location"])


@router.get(
    "/search",
    response_model=LocationSearchResponse,
    summary="Search for a location by name",
    description=(
        "Resolves a free-text place name to one or more matching locations "
        "with coordinates, country, and administrative area information. "
        "All matches are returned — ambiguous queries (e.g. 'Springfield') "
        "return every result so the client can let the user pick. "
        "Returns an empty list when nothing matches."
    ),
)
async def search_location(
    q: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="Place name to search for (e.g. 'Noida', 'Springfield', 'Paris')",
    ),
    count: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum number of results to return (default 10, max 100)",
    ),
) -> LocationSearchResponse:
    """
    Search for locations matching the query string **q**.

    - **q**: free-text place name (required)
    - **count**: max results to return (1–100, default 10)

    Returns a `LocationSearchResponse` with:
    - **query**: the original search string
    - **count**: number of results actually returned
    - **results**: list of `Location` objects (may be empty)
    """
    try:
        locations = await geocode(q, count=count)
    except GeocodingServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc

    return LocationSearchResponse(
        query=q,
        count=len(locations),
        results=locations,
    )
