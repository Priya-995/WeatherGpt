"""
Alert Service — in-memory alert store + normalisation layer + live IMD CAP feed fetcher.

Architecture
------------
                        ┌──────────────────────────────┐
  IMD CAP feed ───────► │  cap_ingest.py               │
                        └──────────────┬───────────────┘
                                       │ Real CAP parsed alerts
                        ┌──────────────▼───────────────┐
                        │  alert_service.py            ├──► in-memory / Supabase store
                        └──────────────┬───────────────┘
                                       │ get_active_alerts(lat, lon / state)
                        ┌──────────────▼───────────────┐
                        │  risk_engine.py / frontend   │
                        └──────────────────────────────┘
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from app.db.supabase_client import get_supabase_client
from app.schemas.alert import Alert, AlertSeverity, AlertType
from app.services.cap_ingest import (
    fetch_and_parse_cap_feed,
    is_uttar_pradesh_alert,
    point_in_polygon,
)

logger = logging.getLogger(__name__)

IMD_CAP_RSS_URL = "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml"

STATE_CENTROIDS: Dict[str, Dict[str, float]] = {
    "Odisha": {"lat": 20.95, "lon": 85.10, "radius_km": 350},
    "West Bengal": {"lat": 22.99, "lon": 87.85, "radius_km": 350},
    "Andhra Pradesh": {"lat": 15.91, "lon": 79.74, "radius_km": 400},
    "Telangana": {"lat": 18.11, "lon": 79.02, "radius_km": 300},
    "Tamil Nadu": {"lat": 11.13, "lon": 78.66, "radius_km": 400},
    "Kerala": {"lat": 10.85, "lon": 76.27, "radius_km": 300},
    "Karnataka": {"lat": 15.32, "lon": 75.71, "radius_km": 400},
    "Maharashtra": {"lat": 19.75, "lon": 75.71, "radius_km": 450},
    "Gujarat": {"lat": 22.26, "lon": 71.19, "radius_km": 400},
    "Madhya Pradesh": {"lat": 22.97, "lon": 78.66, "radius_km": 450},
    "Rajasthan": {"lat": 27.02, "lon": 74.22, "radius_km": 450},
    "Uttar Pradesh": {"lat": 26.85, "lon": 80.91, "radius_km": 450},
    "Bihar": {"lat": 25.10, "lon": 85.31, "radius_km": 300},
    "Jharkhand": {"lat": 23.61, "lon": 85.28, "radius_km": 300},
    "Chhattisgarh": {"lat": 21.28, "lon": 81.87, "radius_km": 300},
    "Assam": {"lat": 26.20, "lon": 92.94, "radius_km": 300},
    "Punjab": {"lat": 31.15, "lon": 75.34, "radius_km": 250},
    "Haryana": {"lat": 29.06, "lon": 76.09, "radius_km": 200},
    "Delhi": {"lat": 28.61, "lon": 77.21, "radius_km": 80},
    "Uttarakhand": {"lat": 30.07, "lon": 79.02, "radius_km": 250},
    "Himachal Pradesh": {"lat": 31.10, "lon": 77.17, "radius_km": 250},
    "Jammu and Kashmir": {"lat": 33.78, "lon": 76.58, "radius_km": 300},
    "Goa": {"lat": 15.30, "lon": 74.12, "radius_km": 80},
    "Sikkim": {"lat": 27.53, "lon": 88.51, "radius_km": 100},
    "Tripura": {"lat": 23.94, "lon": 91.99, "radius_km": 150},
    "Meghalaya": {"lat": 25.47, "lon": 91.37, "radius_km": 150},
    "Manipur": {"lat": 24.66, "lon": 93.91, "radius_km": 150},
    "Mizoram": {"lat": 23.16, "lon": 92.94, "radius_km": 150},
    "Nagaland": {"lat": 26.16, "lon": 94.56, "radius_km": 150},
    "Arunachal Pradesh": {"lat": 28.22, "lon": 94.73, "radius_km": 250},
    "Puducherry": {"lat": 11.94, "lon": 79.81, "radius_km": 60},
}

_store: Dict[str, Alert] = {}  # id → Alert store
_last_good_alerts: List[Alert] = []


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _alert_to_row(alert: Alert) -> dict:
    return {
        "id": alert.id,
        "type": alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type),
        "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
        "affected_location": alert.affected_location,
        "issue_time": alert.issue_time.isoformat() if isinstance(alert.issue_time, datetime) else str(alert.issue_time),
        "expiry_time": alert.expiry_time.isoformat() if isinstance(alert.expiry_time, datetime) else str(alert.expiry_time),
        "source": alert.source,
        "instructions": alert.instructions,
    }


def _row_to_alert(row: dict) -> Alert:
    issue_time = row["issue_time"]
    if isinstance(issue_time, str):
        issue_time = datetime.fromisoformat(issue_time.replace("Z", "+00:00"))
    expiry_time = row["expiry_time"]
    if isinstance(expiry_time, str):
        expiry_time = datetime.fromisoformat(expiry_time.replace("Z", "+00:00"))

    try:
        a_type = AlertType(row.get("type", "other"))
    except ValueError:
        a_type = AlertType.OTHER

    try:
        a_sev = AlertSeverity(row.get("severity", "minor"))
    except ValueError:
        a_sev = AlertSeverity.MINOR

    source = row.get("source", "IMD CAP Live")

    return Alert(
        id=row["id"],
        alert_type=a_type,
        severity=a_sev,
        affected_location=row.get("affected_location", ""),
        issue_time=issue_time,
        expiry_time=expiry_time,
        source=source,
        instructions=row.get("instructions", ""),
        is_mock=False,
    )


def add_alert(alert: Alert) -> Alert:
    """Add or replace an alert in the store."""
    _store[alert.id] = alert
    try:
        supabase = get_supabase_client()
        supabase.table("alerts").upsert(_alert_to_row(alert)).execute()
    except Exception as exc:
        logger.warning("Supabase alert write failed: %s", exc)
    return alert


def get_all_alerts() -> List[Alert]:
    """Return all active stored alerts."""
    _purge_expired_alerts()
    return list(_store.values())


def _purge_expired_alerts() -> None:
    """Drop expired alerts based on real expiry_time."""
    now = _now_utc()
    expired_ids = [aid for aid, a in _store.items() if a.expiry_time <= now]
    for aid in expired_ids:
        del _store[aid]


async def fetch_and_store_alerts() -> List[Alert]:
    """
    Fetch live IMD CAP alerts.
    If live fetch succeeds, update memory store and _last_good_alerts.
    If fetch fails, keep last good alerts (if non-expired).
    Never invent mock alerts.
    Broadcasts any newly discovered alert over WebSocket.
    """
    logger.info("=== fetch_and_store_alerts() called ===")
    now = _now_utc()
    try:
        live_alerts = await fetch_and_parse_cap_feed()
        if live_alerts:
            previous_ids = set(_store.keys())
            new_alerts = [a for a in live_alerts if a.id not in previous_ids]

            _store.clear()
            for alert in live_alerts:
                _store[alert.id] = alert
            global _last_good_alerts
            _last_good_alerts = list(live_alerts)
            logger.info("Updated alert store with %d live CAP alerts.", len(live_alerts))

            if new_alerts:
                from app.api.routes.websocket import broadcast_alert
                for new_a in new_alerts:
                    try:
                        await broadcast_alert(new_a)
                    except Exception as b_err:
                        logger.warning("WebSocket broadcast failed for alert %s: %s", new_a.id, b_err)
        else:
            logger.info("Live CAP feed returned 0 alerts or quiet feed.")
            _purge_expired_alerts()
    except Exception as exc:
        logger.error("Error fetching live IMD CAP feed: %s", exc, exc_info=True)
        _purge_expired_alerts()

    return list(_store.values())


def get_active_alerts(state: Optional[str] = "Uttar Pradesh") -> List[Alert]:
    """
    Return active non-expired alerts, filtered by state if provided.
    Defaults to state="Uttar Pradesh".
    """
    _purge_expired_alerts()
    active = list(_store.values())

    if state and state.strip() and state.strip().lower() not in ("all", "all india"):
        state_query = state.strip().lower()
        filtered: List[Alert] = []
        for alert in active:
            if state_query == "uttar pradesh":
                if is_uttar_pradesh_alert(alert):
                    filtered.append(alert)
            else:
                loc = (alert.affected_location or "").lower()
                desc = (alert.area_desc or "").lower()
                if state_query in loc or state_query in desc:
                    filtered.append(alert)
        active = filtered

    severity_order = {
        AlertSeverity.EXTREME: 0,
        AlertSeverity.SEVERE: 1,
        AlertSeverity.MODERATE: 2,
        AlertSeverity.MINOR: 3,
    }
    return sorted(active, key=lambda a: severity_order.get(a.severity, 9))


def get_active_alerts_for_location(
    lat: float, lon: float, radius_km: float = 300.0
) -> List[Alert]:
    """
    Return active alerts that geographically affect the given coordinates.
    Strictly checks point-in-polygon and centroid radius.
    Alerts without geometry covering the location are NOT returned.
    """
    _purge_expired_alerts()
    active = list(_store.values())
    result: List[Alert] = []

    for alert in active:
        matched = False

        # 1. Check point-in-polygon ray casting if polygons exist
        if alert.polygons:
            for poly in alert.polygons:
                if point_in_polygon(lat, lon, poly):
                    matched = True
                    break

        # 2. Check centroid distance if lat/lon provided
        if not matched and alert.affected_lat is not None and alert.affected_lon is not None:
            dlat = (lat - alert.affected_lat) * 111.0
            dlon = (lon - alert.affected_lon) * 111.0 * 0.85
            dist_km = (dlat ** 2 + dlon ** 2) ** 0.5
            effective_radius = alert.affected_radius_km or radius_km
            if dist_km <= effective_radius:
                matched = True

        if matched:
            result.append(alert)

    severity_order = {
        AlertSeverity.EXTREME: 0,
        AlertSeverity.SEVERE: 1,
        AlertSeverity.MODERATE: 2,
        AlertSeverity.MINOR: 3,
    }
    return sorted(result, key=lambda a: severity_order.get(a.severity, 9))


def get_alert_data_for_risk_engine(
    lat: float, lon: float
) -> Optional[Dict[str, str]]:
    """
    Return the alert_data dict expected by risk_engine.calculate_risk().
    """
    alerts = get_active_alerts_for_location(lat, lon)
    if not alerts:
        return None

    severity_rank = {
        AlertSeverity.MINOR: 1,
        AlertSeverity.MODERATE: 2,
        AlertSeverity.SEVERE: 3,
        AlertSeverity.EXTREME: 4,
    }
    highest = max(alerts, key=lambda a: severity_rank.get(a.severity, 0))
    return {"max_level": highest.severity.value}