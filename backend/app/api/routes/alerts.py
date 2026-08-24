"""
Alerts API router.

Endpoints
---------
GET  /api/alerts                    → list active alerts (all locations)
GET  /api/alerts?lat=..&lon=..      → list active alerts near a location
POST /api/alerts/ingest             → add a new alert + broadcast via WebSocket
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
    normalise_alert,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get(
    "",
    response_model=AlertStoreResponse,
    summary="Get active weather alerts",
    description=(
        "Returns active alerts from live IMD CAP feed or fallback mock data."
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
) -> AlertStoreResponse:
    """
    Returns active alerts. With lat/lon, filters to those affecting the location.
    Without lat/lon, returns all active alerts.
    """
    if lat is not None and lon is not None:
        alerts = get_active_alerts_for_location(lat, lon)
    else:
        alerts = get_active_alerts()

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
    alerts = fetch_and_store_alerts()
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
            "mock_heavy_rain": {
                "summary": "Simulate a heavy rain alert for Delhi",
                "value": {
                    "identifier": "TEST-001",
                    "event": "heavy_rain",
                    "severity": "red",
                    "areaDesc": "South Delhi",
                    "latitude": 28.52,
                    "longitude": 77.18,
                    "radius_km": 50.0,
                    "source": "IMD Live",
                    "description": "Test alert — very heavy rain expected.",
                    "is_mock": False,
                },
            }
        },
    ),
) -> Alert:
    """
    Normalise and store an incoming alert, then push it to WebSocket subscribers.
    """
    try:
        alert = normalise_alert(raw)
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid alert payload: {exc}") from exc

    add_alert(alert)
    logger.info("Alert ingested: %s (%s)", alert.id, alert.severity)

    from app.api.routes.websocket import broadcast_alert
    await broadcast_alert(alert)

    return alert
