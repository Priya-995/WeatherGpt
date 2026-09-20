from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.core.errors import WeatherGPTError
from app.schemas.alerts import Alert, AlertMatch
from app.schemas.geo import Place
from app.services.geocoding import search_places
from app.services.imd_alerts import get_current_alerts, match_location

router = APIRouter()


@router.get("/alerts/imd")
async def get_imd_alerts(
    state: Optional[str] = Query(None, description="Filter alerts by state (case-insensitive substring)"),
    severity: Optional[str] = Query(None, description="Filter alerts by severity (e.g. Severe, Moderate)"),
    event: Optional[str] = Query(None, description="Filter alerts by event (e.g. Heavy rain)"),
):
    alerts, skipped = await get_current_alerts()

    if state:
        st_norm = state.strip().lower()
        alerts = [
            a for a in alerts
            if any(st_norm in (area.area_desc or "").lower() for area in a.areas)
            or (a.headline and st_norm in a.headline.lower())
            or (a.description and st_norm in a.description.lower())
        ]

    if severity:
        sev_norm = severity.strip().lower()
        alerts = [a for a in alerts if a.severity.lower() == sev_norm]

    if event:
        ev_norm = event.strip().lower()
        alerts = [a for a in alerts if ev_norm in a.event.lower()]

    return {
        "source": "IMD",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(alerts),
        "skipped": skipped,
        "alerts": alerts,
    }


@router.get("/alerts/imd/by-location")
async def get_imd_alerts_by_location(
    q: Optional[str] = Query(None, description="Place name to query via geocoding"),
    lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Latitude (-90 to 90)"),
    lon: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Longitude (-180 to 180)"),
):
    # Validation: Either q or both (lat, lon) must be provided
    if not q and (lat is None or lon is None):
        raise HTTPException(
            status_code=422,
            detail="Either 'q' (place name) OR both 'lat' and 'lon' parameters are required"
        )
    if q is None and (lat is None or lon is None):
        raise HTTPException(
            status_code=422,
            detail="Both 'lat' and 'lon' must be provided together when 'q' is omitted"
        )

    target_place: Optional[Place] = None
    target_lat: float = 0.0
    target_lon: float = 0.0

    if q:
        places = await search_places(query=q, limit=1)
        if not places:
            raise WeatherGPTError(
                code="PLACE_NOT_FOUND",
                message=f"Place '{q}' not found",
                status_code=404
            )
        target_place = places[0]
        target_lat = target_place.latitude
        target_lon = target_place.longitude
    else:
        target_lat = lat  # type: ignore
        target_lon = lon  # type: ignore
        target_place = Place(
            id=0,
            name=f"Coordinates ({target_lat}, {target_lon})",
            latitude=target_lat,
            longitude=target_lon,
        )

    current_alerts, _ = await get_current_alerts()
    matches = match_location(current_alerts, target_lat, target_lon, target_place)

    if matches:
        note = f"Found {len(matches)} active IMD alert match(es) for this location."
    else:
        note = "No active IMD alert matched this location at fetch time. This is not a guarantee of safety."

    return {
        "location": target_place.model_dump(),
        "source": "IMD",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(matches),
        "matches": matches,
        "note": note,
    }
