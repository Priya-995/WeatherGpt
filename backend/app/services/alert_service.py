"""
Alert Service — in-memory alert store + normalisation layer.

Architecture
------------
                        ┌──────────────────────┐
  (Section 8) IMD feed ─►  alert_service.py     ├──► in-memory store
  (now)   mock seeding ─►  normalise_alert()    │
                        └──────┬───────────────┘
                               │ get_active_alerts(lat, lon)
                        ┌──────▼───────────────┐
                        │  risk_engine.py       │  official_warning_severity
                        └──────────────────────┘

In-memory store (Section 7 placeholder)
----------------------------------------
Alerts are stored in a module-level list.  Expiry is checked on every read.
Section 8 will replace this with a Supabase table and a real-time subscription.

TODO (Section 8): replace _store and its helpers with Supabase client calls.

Mock data
---------
On import, three realistic mock alerts are seeded that match the shape of real
IMD bulletins (Delhi/NCR heavy rain, Uttar Pradesh thunderstorm, Rajasthan heat
wave).  They all have expiry_time set 24 hours from server startup so they are
immediately active and easy to test against.

To swap in the real IMD feed:
  1. Remove the _seed_mock_alerts() call at module bottom.
  2. Implement fetch_imd_alerts() using httpx to hit the IMD API / TIGGE endpoint.
  3. Call normalise_alert() on each raw bulletin before storing.
  4. Wire a background task (APScheduler / asyncio) to poll every N minutes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.schemas.alert import Alert, AlertSeverity, AlertType


import logging
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Store & Supabase Mappers
# ---------------------------------------------------------------------------

_store: Dict[str, Alert] = {}  # id → Alert fallback store


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

    return Alert(
        id=row["id"],
        alert_type=a_type,
        severity=a_sev,
        affected_location=row.get("affected_location", ""),
        issue_time=issue_time,
        expiry_time=expiry_time,
        source=row.get("source", "IMD"),
        instructions=row.get("instructions", ""),
    )


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def add_alert(alert: Alert) -> Alert:
    """
    Add or replace an alert in the store.
    Callers include the mock seeder, the POST /api/alerts/ingest endpoint.
    Returns the stored alert for chaining.
    """
    _store[alert.id] = alert
    try:
        supabase = get_supabase_client()
        supabase.table("alerts").upsert(_alert_to_row(alert)).execute()
    except Exception as exc:
        logger.warning("Supabase alert write failed: %s", exc)
    return alert


def get_all_alerts() -> List[Alert]:
    """Return all alerts, including expired ones."""
    try:
        supabase = get_supabase_client()
        res = supabase.table("alerts").select("*").execute()
        if res.data is not None:
            return [_row_to_alert(row) for row in res.data]
    except Exception as exc:
        logger.warning("Supabase alerts read failed: %s. Falling back to in-memory store.", exc)
    return list(_store.values())


def get_active_alerts() -> List[Alert]:
    """
    Return only non-expired alerts, ordered most-severe first.
    """
    now_iso = _now_utc().isoformat()
    try:
        supabase = get_supabase_client()
        res = supabase.table("alerts").select("*").gt("expiry_time", now_iso).execute()
        if res.data is not None and len(res.data) > 0:
            alerts = [_row_to_alert(row) for row in res.data]
            severity_order = {
                AlertSeverity.EXTREME: 0,
                AlertSeverity.SEVERE: 1,
                AlertSeverity.MODERATE: 2,
                AlertSeverity.MINOR: 3,
            }
            return sorted(alerts, key=lambda a: severity_order.get(a.severity, 9))
    except Exception as exc:
        logger.warning("Supabase active alerts read failed: %s. Falling back to in-memory store.", exc)

    now = _now_utc()
    expired_ids = [aid for aid, a in _store.items() if a.expiry_time <= now]
    for aid in expired_ids:
        del _store[aid]

    severity_order = {
        AlertSeverity.EXTREME: 0,
        AlertSeverity.SEVERE: 1,
        AlertSeverity.MODERATE: 2,
        AlertSeverity.MINOR: 3,
    }
    return sorted(
        _store.values(),
        key=lambda a: severity_order.get(a.severity, 9),
    )



def get_active_alerts_for_location(
    lat: float, lon: float, radius_km: float = 200.0
) -> List[Alert]:
    """
    Return active alerts that geographically affect the given coordinates.

    Proximity check uses a simple great-circle approximation
    (1° ≈ 111 km).  For alerts without coordinates, they are included
    conservatively (we assume they may cover the queried point).

    Section 8: replace with a PostGIS ST_DWithin query on Supabase.
    """
    active = get_active_alerts()
    result: List[Alert] = []
    for alert in active:
        if alert.affected_lat is None or alert.affected_lon is None:
            result.append(alert)  # no coords → include conservatively
            continue
        # Simple Euclidean approximation in degrees → km
        dlat = (lat - alert.affected_lat) * 111.0
        dlon = (lon - alert.affected_lon) * 111.0 * 0.85  # cos(avg lat) ≈ 0.85 for India
        dist_km = (dlat ** 2 + dlon ** 2) ** 0.5
        effective_radius = alert.affected_radius_km or radius_km
        if dist_km <= effective_radius:
            result.append(alert)
    return result


def get_alert_data_for_risk_engine(
    lat: float, lon: float
) -> Optional[Dict[str, str]]:
    """
    Return the alert_data dict expected by risk_engine.calculate_risk().

    Format: {"max_level": "minor" | "moderate" | "severe" | "extreme"}
    Returns None if no active alerts affect the location.

    The risk engine's official_warning_severity component reads max_level
    and maps it to a 0–1 severity weight.
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


def normalise_alert(raw: dict) -> Alert:
    """
    Normalise a raw IMD bulletin dict into an Alert schema object.

    TODO (Section 8): flesh this out to match the real IMD TIGGE / CAP XML
    fields.  For now it handles the mock dict structure used by _seed_mock_alerts().

    Expected raw keys (matching IMD CAP 1.2 alert element names):
      identifier, event, severity, areaDesc, sent, expires, description,
      latitude (optional), longitude (optional), radius_km (optional)
    """
    severity_map = {
        "yellow":   AlertSeverity.MINOR,
        "orange":   AlertSeverity.MODERATE,
        "red":      AlertSeverity.SEVERE,
        "extreme":  AlertSeverity.EXTREME,
        # already normalised values pass through:
        "minor":    AlertSeverity.MINOR,
        "moderate": AlertSeverity.MODERATE,
        "severe":   AlertSeverity.SEVERE,
    }
    event_map = {
        "heavy_rain":      AlertType.HEAVY_RAIN,
        "very_heavy_rain": AlertType.VERY_HEAVY_RAIN,
        "thunderstorm":    AlertType.THUNDERSTORM,
        "cyclone":         AlertType.CYCLONE,
        "heat_wave":       AlertType.HEAT_WAVE,
        "cold_wave":       AlertType.COLD_WAVE,
        "flood":           AlertType.FLOOD,
        "strong_wind":     AlertType.STRONG_WIND,
        "dense_fog":       AlertType.DENSE_FOG,
        "hailstorm":       AlertType.HAILSTORM,
        "dust_storm":      AlertType.DUST_STORM,
    }

    return Alert(
        id=raw.get("identifier", str(uuid.uuid4())),
        alert_type=event_map.get(raw.get("event", ""), AlertType.OTHER),
        severity=severity_map.get(raw.get("severity", "minor").lower(), AlertSeverity.MINOR),
        affected_location=raw.get("areaDesc", raw.get("affected_location", "Unknown")),
        affected_lat=raw.get("latitude"),
        affected_lon=raw.get("longitude"),
        affected_radius_km=raw.get("radius_km"),
        issue_time=raw.get("sent", _now_utc()),
        expiry_time=raw.get("expires", _now_utc() + timedelta(hours=24)),
        source=raw.get("source", "IMD"),
        instructions=raw.get("description", raw.get("instructions", "No instructions provided.")),
        is_mock=raw.get("is_mock", False),
    )


# ---------------------------------------------------------------------------
# Mock alert seeder
# TODO (Section 8): remove this and replace with real IMD feed poller
# ---------------------------------------------------------------------------

def _seed_mock_alerts() -> None:
    """
    Seed three realistic mock alerts that mirror real IMD bulletins.
    All expire 24 hours from server startup.

    ─── REPLACE THIS FUNCTION IN SECTION 8 ───────────────────────────────
    When the live IMD feed is available:
      1. Delete this function and its call below.
      2. Implement fetch_imd_alerts() with httpx.
      3. Schedule it to run every 30 minutes via a FastAPI lifespan task.
    ───────────────────────────────────────────────────────────────────────
    """
    now = _now_utc()
    expiry = now + timedelta(hours=24)

    mock_bulletins = [
        {
            "identifier": "IMD-MOCK-001-DL-RAIN",
            "event": "heavy_rain",
            "severity": "orange",   # IMD orange → moderate
            "areaDesc": "Delhi / NCR (including Noida, Gurugram, Faridabad)",
            "latitude": 28.61,
            "longitude": 77.21,
            "radius_km": 80.0,
            "sent": now,
            "expires": expiry,
            "source": "IMD Mock",
            "description": (
                "Heavy to very heavy rainfall expected over Delhi/NCR in the next 24 hours. "
                "Residents should avoid travel in low-lying areas. Waterlogging possible in "
                "underpasses and flood-prone zones. Keep emergency contact 1078 (NDRF) handy."
            ),
            "is_mock": True,
        },
        {
            "identifier": "IMD-MOCK-002-UP-TSTORM",
            "event": "thunderstorm",
            "severity": "yellow",   # IMD yellow → minor
            "areaDesc": "Uttar Pradesh (Western districts: Agra, Mathura, Aligarh)",
            "latitude": 27.18,
            "longitude": 78.01,
            "radius_km": 150.0,
            "sent": now,
            "expires": expiry,
            "source": "IMD Mock",
            "description": (
                "Thunderstorm with lightning and gusty winds (40–50 km/h) expected. "
                "Farmers should not work in open fields. Avoid sheltering under isolated trees. "
                "Keep livestock indoors."
            ),
            "is_mock": True,
        },
        {
            "identifier": "IMD-MOCK-003-RJ-HEAT",
            "event": "heat_wave",
            "severity": "red",      # IMD red → severe
            "areaDesc": "Rajasthan (Barmer, Jaisalmer, Bikaner, Churu districts)",
            "latitude": 27.2,
            "longitude": 70.9,
            "radius_km": 200.0,
            "sent": now,
            "expires": expiry,
            "source": "IMD Mock",
            "description": (
                "Severe heat wave conditions. Maximum temperatures likely to exceed 46°C. "
                "Avoid outdoor exposure between 11 AM and 6 PM. Drink water every 30 minutes. "
                "Signs of heat stroke: high body temperature, no sweating, confusion — "
                "call 108 immediately."
            ),
            "is_mock": True,
        },
    ]

    for raw in mock_bulletins:
        alert = normalise_alert(raw)
        add_alert(alert)


# Seed mock data on module import.
# TODO (Section 8): replace with live IMD feed scheduler.
_seed_mock_alerts()
