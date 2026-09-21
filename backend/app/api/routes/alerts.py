"""
Alerts API router.

Endpoints
---------
GET  /api/alerts                    → list active alerts for Uttar Pradesh (default) or specified state
GET  /api/alerts?state=all          → list active alerts for all India
GET  /api/alerts?lat=..&lon=..      → list active alerts near a location (point-in-polygon)
POST /api/alerts/refresh            → re-fetch live IMD CAP feed + broadcast via WebSocket
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Query

from app.schemas.alert import Alert, AlertStoreResponse
from app.services.alert_service import (
    add_alert,
    fetch_and_store_alerts,
    get_active_alerts,
    get_active_alerts_for_location,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get(
    "",
    response_model=AlertStoreResponse,
    summary="Get active weather alerts",
    description=(
        "Returns active weather alerts from official IMD CAP feed. "
        "Defaults to Uttar Pradesh alerts (?state=Uttar%20Pradesh). Use ?state=all for all India."
    ),
)
async def list_alerts(
    lat: Optional[float] = Query(
        None, ge=-90.0, le=90.0,
        description="Filter: latitude of the point of interest"
    ),
    lon: Optional[float] = Query(
        None, ge=-180.0, le=180.0,
        description="Filter: longitude of the point of interest"
    ),
    state: Optional[str] = Query(
        "Uttar Pradesh",
        description="Filter: state name (defaults to 'Uttar Pradesh'). Pass 'all' for all India."
    ),
) -> AlertStoreResponse:
    """
    Returns active alerts. With lat/lon, filters to those affecting the location via geometry/polygon.
    Without lat/lon, filters by state parameter (defaults to Uttar Pradesh).
    """
    if lat is not None and lon is not None:
        alerts = get_active_alerts_for_location(lat, lon)
    else:
        alerts = get_active_alerts(state=state)

    return AlertStoreResponse(active_count=len(alerts), alerts=alerts)


@router.post(
    "/refresh",
    response_model=AlertStoreResponse,
    summary="Refresh live IMD CAP alerts feed",
    description="Re-fetches the live IMD CAP feed and broadcasts alerts over WebSockets.",
)
async def refresh_alerts_endpoint() -> AlertStoreResponse:
    """
    Re-fetch live IMD alerts feed and broadcast updates.
    """
    logger.info("=== /api/alerts/refresh endpoint hit ===")
    alerts = await fetch_and_store_alerts()
    if alerts:
        from app.api.routes.websocket import broadcast_alert
        try:
            await broadcast_alert(alerts[0])
        except Exception as exc:
            logger.warning("WebSocket alert broadcast failed: %s", exc)

    return AlertStoreResponse(active_count=len(alerts), alerts=alerts)


@router.post(
    "/ingest",
    response_model=Alert,
    summary="Ingest a new alert and broadcast to WebSocket clients",
    status_code=201,
)
async def ingest_alert(
    raw: dict = Body(
        ...,
        examples={
            "heavy_rain_up": {
                "summary": "Simulate a heavy rain alert for Uttar Pradesh",
                "value": {
                    "identifier": "TEST-UP-001",
                    "event": "heavy_rain",
                    "severity": "orange",
                    "areaDesc": "East Uttar Pradesh, Lucknow",
                    "source": "IMD CAP Live",
                    "description": "Heavy rainfall warning for East Uttar Pradesh.",
                    "is_mock": False,
                },
            }
        },
    ),
) -> Alert:
    """
    Normalise and store an incoming alert, then push it to WebSocket subscribers.
    """
    from app.services.cap_ingest import map_cap_event_type, map_cap_severity
    try:
        alert = Alert(
            id=raw.get("identifier", "TEST-001"),
            alert_type=map_cap_event_type(raw.get("event", ""), raw.get("description", "")),
            severity=map_cap_severity(raw.get("severity", "minor")),
            affected_location=raw.get("areaDesc", raw.get("affected_location", "Uttar Pradesh")),
            affected_lat=raw.get("latitude"),
            affected_lon=raw.get("longitude"),
            affected_radius_km=raw.get("radius_km"),
            issue_time=raw.get("issue_time") or raw.get("sent") or "2026-09-21T00:00:00Z",
            expiry_time=raw.get("expiry_time") or raw.get("expires") or "2026-09-22T00:00:00Z",
            source=raw.get("source", "IMD CAP Live"),
            instructions=raw.get("description", raw.get("instructions", "No instructions.")),
            is_mock=False,
            area_desc=raw.get("areaDesc"),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid alert payload: {exc}") from exc

    add_alert(alert)
    logger.info("Alert ingested: %s (%s)", alert.id, alert.severity)

    from app.api.routes.websocket import broadcast_alert
    await broadcast_alert(alert)

    return alert
