"""
Alert Service — in-memory alert store + normalisation layer + live IMD CAP RSS feed fetcher.

Architecture
------------
                        ┌──────────────────────────────┐
  IMD CAP RSS feed ───► │  fetch_live_imd_alerts()     │
                        └──────────────┬───────────────┘
                                       │ fallback if empty/error
                        ┌──────────────▼───────────────┐
  Mock generator ─────► │  _seed_mock_alerts()         ├──► in-memory / Supabase store
                        └──────────────┬───────────────┘
                                       │ get_active_alerts(lat, lon)
                        ┌──────────────▼───────────────┐
                        │  risk_engine.py              │  official_warning_severity
                        └──────────────────────────────┘
"""

from __future__ import annotations

import logging
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional

import httpx

from app.db.supabase_client import get_supabase_client
from app.schemas.alert import Alert, AlertSeverity, AlertType

logger = logging.getLogger(__name__)

IMD_CAP_RSS_URL = "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml"

# ---------------------------------------------------------------------------
# Store & Supabase Mappers
# ---------------------------------------------------------------------------

_store: Dict[str, Alert] = {}  # id → Alert store


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

    source = row.get("source", "IMD Live")
    is_mock = "mock" in source.lower()

    return Alert(
        id=row["id"],
        alert_type=a_type,
        severity=a_sev,
        affected_location=row.get("affected_location", ""),
        issue_time=issue_time,
        expiry_time=expiry_time,
        source=source,
        instructions=row.get("instructions", ""),
        is_mock=is_mock,
    )


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def add_alert(alert: Alert) -> Alert:
    """
    Add or replace an alert in the store.
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
        if res.data is not None and len(res.data) > 0:
            return [_row_to_alert(row) for row in res.data]
    except Exception as exc:
        logger.warning("Supabase alerts read failed: %s. Falling back to in-memory store.", exc)
    return list(_store.values())


def get_active_alerts() -> List[Alert]:
    """
    Return only non-expired alerts, ordered most-severe first.
    If store has only mock alerts or is empty, attempts a live IMD fetch.
    """
    has_only_mocks = not _store or all(getattr(a, "is_mock", False) or "mock" in (a.source or "").lower() for a in _store.values())
    if has_only_mocks:
        fetch_and_store_alerts()

    now_iso = _now_utc().isoformat()
    try:
        supabase = get_supabase_client()
        res = supabase.table("alerts").select("*").gt("expiry_time", now_iso).execute()
        if res.data is not None and len(res.data) > 0:
            alerts = [_row_to_alert(row) for row in res.data]
            live_alerts = [a for a in alerts if a.source == "IMD Live" or not a.is_mock]
            if live_alerts:
                severity_order = {
                    AlertSeverity.EXTREME: 0,
                    AlertSeverity.SEVERE: 1,
                    AlertSeverity.MODERATE: 2,
                    AlertSeverity.MINOR: 3,
                }
                return sorted(live_alerts, key=lambda a: severity_order.get(a.severity, 9))
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
    """
    active = get_active_alerts()
    result: List[Alert] = []
    for alert in active:
        if alert.affected_lat is None or alert.affected_lon is None:
            result.append(alert)
            continue
        dlat = (lat - alert.affected_lat) * 111.0
        dlon = (lon - alert.affected_lon) * 111.0 * 0.85
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


def _infer_alert_type(title: str, desc: str) -> AlertType:
    text = (title + " " + desc).lower()
    if "extremely heavy" in text or "very heavy rain" in text:
        return AlertType.VERY_HEAVY_RAIN
    if "heavy rain" in text or "rainfall" in text:
        return AlertType.HEAVY_RAIN
    if "thunderstorm" in text or "lightning" in text:
        return AlertType.THUNDERSTORM
    if "cyclone" in text or "depress" in text:
        return AlertType.CYCLONE
    if "heat wave" in text or "heatwave" in text:
        return AlertType.HEAT_WAVE
    if "cold wave" in text or "coldwave" in text:
        return AlertType.COLD_WAVE
    if "flood" in text:
        return AlertType.FLOOD
    if "wind" in text or "gale" in text:
        return AlertType.STRONG_WIND
    if "fog" in text:
        return AlertType.DENSE_FOG
    if "hail" in text:
        return AlertType.HAILSTORM
    if "dust" in text:
        return AlertType.DUST_STORM
    return AlertType.OTHER


def normalise_alert(raw: dict) -> Alert:
    """
    Normalise a raw alert dict into an Alert schema object.
    """
    severity_map = {
        "yellow": AlertSeverity.MINOR,
        "orange": AlertSeverity.MODERATE,
        "red": AlertSeverity.SEVERE,
        "extreme": AlertSeverity.EXTREME,
        "minor": AlertSeverity.MINOR,
        "moderate": AlertSeverity.MODERATE,
        "severe": AlertSeverity.SEVERE,
    }
    event_map = {
        "heavy_rain": AlertType.HEAVY_RAIN,
        "very_heavy_rain": AlertType.VERY_HEAVY_RAIN,
        "thunderstorm": AlertType.THUNDERSTORM,
        "cyclone": AlertType.CYCLONE,
        "heat_wave": AlertType.HEAT_WAVE,
        "cold_wave": AlertType.COLD_WAVE,
        "flood": AlertType.FLOOD,
        "strong_wind": AlertType.STRONG_WIND,
        "dense_fog": AlertType.DENSE_FOG,
        "hailstorm": AlertType.HAILSTORM,
        "dust_storm": AlertType.DUST_STORM,
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
        source=raw.get("source", "IMD Live"),
        instructions=raw.get("description", raw.get("instructions", "No instructions provided.")),
        is_mock=raw.get("is_mock", False),
    )


# ---------------------------------------------------------------------------
# Live IMD CAP RSS Feed Fetcher & Fallback
# ---------------------------------------------------------------------------

def fetch_live_imd_alerts() -> List[Alert]:
    """
    Fetch and parse live CAP alerts from the IMD public RSS feed.
    Maps CAP/RSS fields to Alert schema with source="IMD Live".
    If fetch fails, times out, or returns zero alerts, returns empty list.
    """
    ns = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}
    try:
        with httpx.Client(timeout=4.0) as client:
            resp = client.get(IMD_CAP_RSS_URL)
            if resp.status_code != 200:
                logger.warning("IMD RSS feed returned HTTP %s", resp.status_code)
                return []

            root = ET.fromstring(resp.text)
            items = root.findall(".//item")
            if not items:
                logger.info("IMD RSS feed returned 0 active alert items.")
                return []

            live_alerts: List[Alert] = []
            for item in items:
                title = item.findtext("title", "")
                desc = item.findtext("description", "")
                guid = item.findtext("guid", "")
                link = item.findtext("link", "")
                pub_date_str = item.findtext("pubDate", "")

                event_title = title or "Weather Warning"
                severity = AlertSeverity.SEVERE if "extremely" in desc.lower() or "extremely" in title.lower() else AlertSeverity.MODERATE
                affected_location = "India"
                if " over " in desc:
                    affected_location = desc.split(" over ")[-1].strip(". ")
                elif " in " in desc:
                    affected_location = desc.split(" in ")[-1].strip(". ")

                instructions = desc or "Exercise caution and follow IMD safety directives."
                issue_time = _now_utc()

                if pub_date_str:
                    try:
                        dt = parsedate_to_datetime(pub_date_str)
                        if dt:
                            issue_time = dt
                    except Exception:
                        pass

                expiry_time = max(_now_utc() + timedelta(hours=48), issue_time + timedelta(hours=48))

                # Fast attempt for detail CAP XML
                if link and link.endswith(".xml"):
                    try:
                        dresp = client.get(link, timeout=1.0)
                        if dresp.status_code == 200:
                            droot = ET.fromstring(dresp.text)
                            info = droot.find("cap:info", ns)
                            if info is not None:
                                cap_sev = (info.findtext("cap:severity", "", ns) or "").lower()
                                if cap_sev == "extreme":
                                    severity = AlertSeverity.EXTREME
                                elif cap_sev == "severe":
                                    severity = AlertSeverity.SEVERE
                                elif cap_sev == "moderate":
                                    severity = AlertSeverity.MODERATE
                                elif cap_sev == "minor":
                                    severity = AlertSeverity.MINOR

                                area_elem = info.find("cap:area", ns)
                                if area_elem is not None:
                                    area_desc = area_elem.findtext("cap:areaDesc", "", ns)
                                    if area_desc:
                                        affected_location = area_desc
                    except Exception:
                        pass

                alert_type = _infer_alert_type(event_title, desc)
                alert_id = guid or link or f"IMD-LIVE-{len(live_alerts)+1}"

                alert = Alert(
                    id=alert_id,
                    alert_type=alert_type,
                    severity=severity,
                    affected_location=affected_location,
                    issue_time=issue_time,
                    expiry_time=expiry_time,
                    source="IMD Live",
                    instructions=instructions,
                    is_mock=False,
                )
                live_alerts.append(alert)

            return live_alerts

    except Exception as exc:
        logger.warning("Failed to fetch live IMD CAP alerts: %s", exc)
        return []


def _seed_mock_alerts() -> None:
    """
    Seed realistic mock alerts labeled source="IMD Mock".
    Used as a robust fallback when live feed is empty or unavailable.
    """
    now = _now_utc()
    expiry = now + timedelta(hours=24)

    mock_bulletins = [
        {
            "identifier": "IMD-MOCK-001-DL-RAIN",
            "event": "heavy_rain",
            "severity": "orange",
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
            "severity": "yellow",
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
            "severity": "red",
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
                "Call 108 immediately if feeling dizzy."
            ),
            "is_mock": True,
        },
    ]

    for raw in mock_bulletins:
        alert = normalise_alert(raw)
        add_alert(alert)


def fetch_and_store_alerts() -> List[Alert]:
    """
    Attempts to fetch live IMD alerts. If found, stores them with source="IMD Live".
    If none found or request fails, seeds mock fallback alerts with source="IMD Mock".
    """
    live_alerts = fetch_live_imd_alerts()
    if live_alerts:
        logger.info("Successfully fetched %d live IMD alerts.", len(live_alerts))
        _store.clear()
        for a in live_alerts:
            add_alert(a)
    else:
        logger.info("No live IMD alerts found or feed unavailable. Falling back to IMD Mock alerts.")
        if not _store:
            _seed_mock_alerts()

    return list(_store.values())


# Fetch live alerts on startup
fetch_and_store_alerts()
