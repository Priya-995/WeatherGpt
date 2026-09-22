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

import asyncio
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
from app.services.imd_subdivision_ingest import fetch_imd_subdivision_alerts
from app.services.imd_district_ingest import fetch_imd_district_alerts

logger = logging.getLogger(__name__)

IMD_CAP_RSS_URL = "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml"

STATE_SUBDIVISION_MAP: Dict[str, List[str]] = {
    "uttar pradesh": ["uttar pradesh", "east uttar pradesh", "west uttar pradesh"],
    "maharashtra": ["maharashtra", "konkan", "goa", "madhya maharashtra", "marathwada", "vidarbha"],
    "west bengal": ["west bengal", "sub-himalayan west bengal", "gangetic west bengal", "sikkim"],
    "rajasthan": ["rajasthan", "east rajasthan", "west rajasthan"],
    "madhya pradesh": ["madhya pradesh", "east madhya pradesh", "west madhya pradesh"],
    "gujarat": ["gujarat", "gujarat region", "saurashtra", "kutch"],
    "karnataka": ["karnataka", "coastal karnataka", "north interior karnataka", "south interior karnataka"],
    "tamil nadu": ["tamil nadu", "puducherry", "karaikal"],
    "andhra pradesh": ["andhra pradesh", "coastal andhra pradesh", "rayalaseema", "yanam"],
    "telangana": ["telangana"],
    "kerala": ["kerala", "mahe"],
    "odisha": ["odisha", "orissa"],
    "bihar": ["bihar"],
    "jharkhand": ["jharkhand"],
    "chhattisgarh": ["chhattisgarh"],
    "assam": ["assam", "meghalaya"],
    "punjab": ["punjab"],
    "haryana": ["haryana", "chandigarh", "delhi"],
    "delhi": ["delhi", "haryana", "chandigarh"],
    "uttarakhand": ["uttarakhand"],
    "himachal pradesh": ["himachal pradesh"],
    "jammu and kashmir": ["jammu", "kashmir", "ladakh"],
    "goa": ["goa", "konkan"],
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
    Fetch live IMD CAP RSS alerts, IMD Subdivision GIS warnings, and IMD District GIS warnings.
    If live fetch succeeds, update memory store and _last_good_alerts.
    If fetch fails, keep last good alerts (if non-expired).
    Never invent mock alerts.
    Broadcasts any newly discovered alert over WebSocket.
    """
    logger.info("=== fetch_and_store_alerts() called ===")
    now = _now_utc()
    try:
        # Fetch CAP RSS feed, Subdivision GIS feed, & District GIS feed concurrently
        cap_alerts, gis_alerts, dist_alerts = await asyncio.gather(
            fetch_and_parse_cap_feed(),
            fetch_imd_subdivision_alerts(),
            fetch_imd_district_alerts(),
            return_exceptions=True
        )

        all_live: List[Alert] = []

        if isinstance(cap_alerts, list):
            all_live.extend(cap_alerts)
        elif isinstance(cap_alerts, Exception):
            logger.error("CAP feed fetch failed: %s", cap_alerts)

        if isinstance(gis_alerts, list):
            all_live.extend(gis_alerts)
        elif isinstance(gis_alerts, Exception):
            logger.error("IMD Subdivision GIS fetch failed: %s", gis_alerts)

        if isinstance(dist_alerts, list):
            all_live.extend(dist_alerts)
        elif isinstance(dist_alerts, Exception):
            logger.error("IMD District GIS fetch failed: %s", dist_alerts)

        if all_live:
            previous_ids = set(_store.keys())
            new_alerts = [a for a in all_live if a.id not in previous_ids]

            _store.clear()
            for alert in all_live:
                _store[alert.id] = alert

            global _last_good_alerts
            _last_good_alerts = list(all_live)
            logger.info(
                "Updated alert store with %d live IMD alerts (%d CAP, %d Subdiv GIS, %d District GIS).",
                len(all_live),
                len(cap_alerts) if isinstance(cap_alerts, list) else 0,
                len(gis_alerts) if isinstance(gis_alerts, list) else 0,
                len(dist_alerts) if isinstance(dist_alerts, list) else 0,
            )

            if new_alerts:
                from app.api.routes.websocket import broadcast_alert
                for new_a in new_alerts:
                    try:
                        await broadcast_alert(new_a)
                    except Exception as b_err:
                        logger.warning("WebSocket broadcast failed for alert %s: %s", new_a.id, b_err)
        else:
            logger.info("Live IMD feeds returned 0 alerts or quiet feed.")
            _purge_expired_alerts()

    except Exception as exc:
        logger.error("Error in fetch_and_store_alerts: %s", exc, exc_info=True)
        _purge_expired_alerts()

    return list(_store.values())


def get_active_alerts(
    state: Optional[str] = "Uttar Pradesh",
    district: Optional[str] = None,
) -> List[Alert]:
    """
    Return active non-expired alerts, filtered by state and/or district if provided.
    Pass state="all" or "All India" for all India alerts.
    """
    _purge_expired_alerts()
    active = list(_store.values())

    # Filter by District if district parameter provided
    if district and district.strip():
        dist_query = district.strip().lower()
        active = [
            alert for alert in active
            if dist_query in (alert.affected_location or "").lower()
            or dist_query in (alert.area_desc or "").lower()
            or dist_query in (alert.instructions or "").lower()
        ]

    # Filter by State if provided (and not 'all' / 'all india')
    if state and state.strip() and state.strip().lower() not in ("all", "all india"):
        state_query = state.strip().lower()
        subdiv_keywords = STATE_SUBDIVISION_MAP.get(state_query, [state_query])

        filtered: List[Alert] = []
        for alert in active:
            if state_query == "uttar pradesh" and is_uttar_pradesh_alert(alert):
                filtered.append(alert)
                continue

            loc = (alert.affected_location or "").lower()
            desc = (alert.area_desc or "").lower()

            matched = any(kw in loc or kw in desc for kw in subdiv_keywords)
            if matched:
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