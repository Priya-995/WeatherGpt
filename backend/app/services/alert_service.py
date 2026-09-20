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
# Indian state / UT name → approximate centroid + typical radius.
#
# Used for two honest purposes only:
#   1. Detecting which real region(s) a bulletin's TITLE actually names,
#      instead of guessing from wherever a sentence happens to end.
#   2. Giving a live alert *some* approximate lat/lon so location-based
#      filtering (get_active_alerts_for_location) isn't silently bypassed
#      for every live alert (it was — see affected_lat/affected_lon below).
#
# These are coarse state-level centroids, not precise district data.
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# IMD meteorological sub-division → parent state.
#
# IMD bulletins frequently name sub-divisions instead of full states.
# We map every official sub-division to its parent state so that
# _match_known_regions() can still resolve a centroid even when the
# bulletin body only names "Vidarbha" or "Rayalaseema" etc.
# ---------------------------------------------------------------------------
SUBDIVISION_TO_STATE: Dict[str, str] = {
    # Gujarat
    "Saurashtra and Kutch": "Gujarat",
    "Saurashtra & Kutch": "Gujarat",
    "North Gujarat": "Gujarat",
    "South Gujarat": "Gujarat",
    # Maharashtra
    "Marathwada": "Maharashtra",
    "Vidarbha": "Maharashtra",
    "Konkan and Goa": "Maharashtra",
    "Konkan & Goa": "Maharashtra",
    "Konkan": "Maharashtra",
    "Madhya Maharashtra": "Maharashtra",
    # Madhya Pradesh / UP
    "Malwa": "Madhya Pradesh",
    "Bundelkhand": "Uttar Pradesh",
    # Andhra Pradesh
    "Rayalaseema": "Andhra Pradesh",
    "Coastal Andhra Pradesh": "Andhra Pradesh",
    "Coastal Andhra": "Andhra Pradesh",
    "North Coastal Andhra Pradesh": "Andhra Pradesh",
    "South Coastal Andhra Pradesh": "Andhra Pradesh",
    # Karnataka
    "Coastal Karnataka": "Karnataka",
    "North Interior Karnataka": "Karnataka",
    "South Interior Karnataka": "Karnataka",
    "Interior Karnataka": "Karnataka",
    # Tamil Nadu
    "Coastal Tamil Nadu": "Tamil Nadu",
    "North Tamil Nadu": "Tamil Nadu",
    "South Tamil Nadu": "Tamil Nadu",
    # West Bengal
    "Gangetic West Bengal": "West Bengal",
    "Sub-Himalayan West Bengal": "West Bengal",
    "Sub Himalayan West Bengal": "West Bengal",
    # Rajasthan
    "East Rajasthan": "Rajasthan",
    "West Rajasthan": "Rajasthan",
    # Uttar Pradesh
    "East Uttar Pradesh": "Uttar Pradesh",
    "West Uttar Pradesh": "Uttar Pradesh",
    # Kerala
    "Lakshadweep": "Kerala",
    # Assam & NE
    "Assam and Meghalaya": "Assam",
    "Assam & Meghalaya": "Assam",
    "Nagaland, Manipur, Mizoram and Tripura": "Nagaland",
    "Arunachal Pradesh": "Arunachal Pradesh",
    # Bihar / Jharkhand
    "North Bihar": "Bihar",
    "South Bihar": "Bihar",
    "North Jharkhand": "Jharkhand",
    "South Jharkhand": "Jharkhand",
    # Himachal / J&K
    "Jammu": "Jammu and Kashmir",
    "Kashmir": "Jammu and Kashmir",
    "Himachal": "Himachal Pradesh",
    # Odisha
    "North Odisha": "Odisha",
    "South Odisha": "Odisha",
    "Interior Odisha": "Odisha",
    "Coastal Odisha": "Odisha",
    # Haryana / Punjab
    "Haryana and Chandigarh": "Haryana",
    "Haryana & Chandigarh": "Haryana",
    "Punjab and Chandigarh": "Punjab",
    "Punjab & Chandigarh": "Punjab",
    # Uttarakhand
    "Kumaon": "Uttarakhand",
    "Garhwal": "Uttarakhand",
    # Chhattisgarh
    "North Chhattisgarh": "Chhattisgarh",
    "South Chhattisgarh": "Chhattisgarh",
}

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


def _seed_mock_alerts() -> List[Alert]:
    """
    Seed active mock alerts for key Indian locations (Delhi NCR, Mumbai, Odisha/West Bengal, Rajasthan)
    so that active alerts are always available when the live IMD feed is quiet or unreachable.
    """
    now = _now_utc()
    mocks = [
        Alert(
            id="MOCK-ALERT-DELHI-001",
            alert_type=AlertType.THUNDERSTORM,
            severity=AlertSeverity.SEVERE,
            affected_location="Delhi / NCR, Haryana",
            affected_lat=28.6139,
            affected_lon=77.2090,
            affected_radius_km=150.0,
            issue_time=now - timedelta(hours=1),
            expiry_time=now + timedelta(hours=23),
            source="IMD Warning Feed (Fallback)",
            instructions="Severe thunderstorm with isolated heavy rainfall and lightning expected over Delhi-NCR. Postpone outdoor activities and avoid waterlogged roads.",
            is_mock=True,
        ),
        Alert(
            id="MOCK-ALERT-ODISHA-002",
            alert_type=AlertType.VERY_HEAVY_RAIN,
            severity=AlertSeverity.EXTREME,
            affected_location="Odisha, West Bengal",
            affected_lat=20.9500,
            affected_lon=85.1000,
            affected_radius_km=350.0,
            issue_time=now - timedelta(hours=2),
            expiry_time=now + timedelta(hours=46),
            source="IMD Warning Feed (Fallback)",
            instructions="Extremely heavy rainfall and gale winds expected in coastal districts of Odisha & Gangetic West Bengal. Fishermen advised not to venture into deep sea.",
            is_mock=True,
        ),
        Alert(
            id="MOCK-ALERT-MUMBAI-003",
            alert_type=AlertType.HEAVY_RAIN,
            severity=AlertSeverity.MODERATE,
            affected_location="Mumbai, Thane, Konkan Region",
            affected_lat=19.0760,
            affected_lon=72.8777,
            affected_radius_km=200.0,
            issue_time=now - timedelta(hours=3),
            expiry_time=now + timedelta(hours=21),
            source="IMD Warning Feed (Fallback)",
            instructions="Moderate to heavy rainfall warning for Mumbai metro and Konkan belt. Commuters check traffic advisories for low-lying underpasses.",
            is_mock=True,
        ),
        Alert(
            id="MOCK-ALERT-RAJASTHAN-004",
            alert_type=AlertType.HEAT_WAVE,
            severity=AlertSeverity.MODERATE,
            affected_location="West Rajasthan",
            affected_lat=27.0238,
            affected_lon=74.2179,
            affected_radius_km=300.0,
            issue_time=now - timedelta(hours=4),
            expiry_time=now + timedelta(hours=20),
            source="IMD Warning Feed (Fallback)",
            instructions="Heat wave conditions at isolated places in West Rajasthan. Avoid direct sun exposure between 12 PM and 4 PM. Stay hydrated.",
            is_mock=True,
        ),
    ]

    for m in mocks:
        _store[m.id] = m
    logger.info("Seeded %d fallback mock alerts into alert store.", len(mocks))
    return mocks


def get_active_alerts() -> List[Alert]:
    """
    Return only non-expired alerts, ordered most-severe first.
    If store is empty or has no active alerts, triggers fetch/seeding.
    """
    now = _now_utc()
    expired_ids = [aid for aid, a in _store.items() if a.expiry_time <= now]
    for aid in expired_ids:
        del _store[aid]

    if not _store:
        fetch_and_store_alerts()

    try:
        supabase = get_supabase_client()
        now_iso = now.isoformat()
        res = supabase.table("alerts").select("*").gt("expiry_time", now_iso).execute()
        if res.data is not None and len(res.data) > 0:
            alerts = [_row_to_alert(row) for row in res.data]
            if alerts:
                severity_order = {
                    AlertSeverity.EXTREME: 0,
                    AlertSeverity.SEVERE: 1,
                    AlertSeverity.MODERATE: 2,
                    AlertSeverity.MINOR: 3,
                }
                return sorted(alerts, key=lambda a: severity_order.get(a.severity, 9))
    except Exception as exc:
        logger.warning("Supabase active alerts read failed: %s. Falling back to in-memory store.", exc)

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
    lat: float, lon: float, radius_km: float = 300.0
) -> List[Alert]:
    """
    Return active alerts that geographically affect the given coordinates.
    If no location-specific alert is within radius_km, returns active national alerts.
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
        effective_radius = max(alert.affected_radius_km or radius_km, radius_km)
        if dist_km <= effective_radius:
            result.append(alert)

    if not result and active:
        return active

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


def _match_known_regions(text: str) -> List[str]:
    """
    Scan `text` for official Indian state/UT names AND standard IMD
    meteorological sub-division names, returning the resolved parent-state
    name for every match found.

    Sub-divisions are checked first (longest-match wins over state-only
    hits), then plain state names. Duplicates are suppressed.
    """
    lower_text = text.lower()
    found: List[str] = []

    # Check sub-divisions first so that e.g. "Coastal Andhra Pradesh" resolves
    # to "Andhra Pradesh" (via subdivision map) rather than being skipped.
    for subdiv, parent_state in SUBDIVISION_TO_STATE.items():
        if subdiv.lower() in lower_text and parent_state not in found:
            found.append(parent_state)

    # Also scan for plain state names not already captured.
    for state_name in STATE_CENTROIDS:
        if state_name.lower() in lower_text and state_name not in found:
            found.append(state_name)

    return found


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
    logger.info("=== fetch_live_imd_alerts() called ===")
    ns = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}
    try:
        with httpx.Client(timeout=4.0) as client:
            resp = client.get(IMD_CAP_RSS_URL)
            if resp.status_code != 200:
                logger.warning("IMD RSS feed returned HTTP %s", resp.status_code)
                return []

            root = ET.fromstring(resp.text)
            items = root.findall(".//item")
            # BUG 3 FIX — log raw count so we can distinguish "feed is quiet"
            # from "our code is silently dropping items".
            logger.info("IMD RSS feed returned %d raw items before filtering.", len(items))
            if not items:
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

                # BUG 1 FIX — description-first matching priority:
                # The specific affected-area detail lives in the description;
                # fall back to the (shorter) title only if nothing matches there.
                desc_regions = _match_known_regions(desc)
                title_regions = _match_known_regions(title)

                if desc_regions:
                    matched_regions = desc_regions
                    if title_regions and set(title_regions) != set(desc_regions):
                        logger.debug(
                            "Region mismatch — title suggested %r but description named %r — using description.",
                            title_regions, desc_regions,
                        )
                elif title_regions:
                    matched_regions = title_regions
                else:
                    matched_regions = []

                if matched_regions:
                    affected_location = ", ".join(matched_regions)
                    geo_state = matched_regions[0]
                else:
                    affected_location = "Region unspecified (see instructions)"
                    geo_state = None

                affected_lat: Optional[float] = None
                affected_lon: Optional[float] = None
                affected_radius_km: Optional[float] = None
                if geo_state and geo_state in STATE_CENTROIDS:
                    centroid = STATE_CENTROIDS[geo_state]
                    affected_lat = centroid["lat"]
                    affected_lon = centroid["lon"]
                    affected_radius_km = centroid["radius_km"]

                instructions = desc or "Exercise caution and follow IMD safety directives."
                issue_time = _now_utc()

                if pub_date_str:
                    try:
                        dt = parsedate_to_datetime(pub_date_str)
                        if dt:
                            issue_time = dt
                    except Exception:
                        pass

                # BUG 2 FIX — expiry anchored to issue_time, not "now".
                # Using max(now+48h, issue_time+48h) caused every alert's
                # expiry to slide forward on every refresh, making old
                # bulletins immortal. Strict issue_time + 48h is correct.
                expiry_time = issue_time + timedelta(hours=48)

                # Attempt to fetch the real per-item CAP detail XML for the
                # authoritative severity + areaDesc. Previously this only ran
                # when the RSS <link> happened to end in ".xml" — real CAP
                # links don't reliably follow that convention, so most items
                # silently skipped this and fell back to the guess above.
                # Now we just try it whenever a link exists.
                if link:
                    try:
                        dresp = client.get(link, timeout=2.0)
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

                                # BUG 2 FIX — read real CAP effective/expires
                                # instead of always guessing issue_time±48h.
                                cap_effective_str = info.findtext("cap:effective", "", ns)
                                cap_expires_str = info.findtext("cap:expires", "", ns)
                                if cap_effective_str:
                                    try:
                                        issue_time = datetime.fromisoformat(
                                            cap_effective_str.replace("Z", "+00:00")
                                        )
                                    except Exception:
                                        pass
                                if cap_expires_str:
                                    try:
                                        expiry_time = datetime.fromisoformat(
                                            cap_expires_str.replace("Z", "+00:00")
                                        )
                                    except Exception:
                                        # Fall back to issue_time + 48h already set above
                                        expiry_time = issue_time + timedelta(hours=48)
                                else:
                                    # No CAP expires field — re-anchor to the
                                    # (possibly updated) issue_time from cap:effective.
                                    expiry_time = issue_time + timedelta(hours=48)

                                # A CAP alert can list multiple <area> blocks
                                # (e.g. one per affected district). Collect
                                # every areaDesc rather than just the first.
                                area_descs = [
                                    a.findtext("cap:areaDesc", "", ns)
                                    for a in info.findall("cap:area", ns)
                                ]
                                area_descs = [a for a in area_descs if a]
                                if area_descs:
                                    affected_location = ", ".join(area_descs)
                                    # Re-run region matching against the real
                                    # areaDesc text so we can still attach
                                    # approximate coordinates.
                                    cap_regions = _match_known_regions(affected_location)
                                    if cap_regions:
                                        centroid = STATE_CENTROIDS[cap_regions[0]]
                                        affected_lat = centroid["lat"]
                                        affected_lon = centroid["lon"]
                                        affected_radius_km = centroid["radius_km"]
                    except Exception as exc:
                        logger.debug("CAP detail fetch failed for %s: %s", link, exc)

                logger.debug(
                    "IMD RSS item parsed — title=%r location=%r lat=%s lon=%s",
                    title, affected_location, affected_lat, affected_lon,
                )

                alert_type = _infer_alert_type(event_title, desc)
                alert_id = guid or link or f"IMD-LIVE-{len(live_alerts)+1}"

                alert = Alert(
                    id=alert_id,
                    alert_type=alert_type,
                    severity=severity,
                    affected_location=affected_location,
                    affected_lat=affected_lat,
                    affected_lon=affected_lon,
                    affected_radius_km=affected_radius_km,
                    issue_time=issue_time,
                    expiry_time=expiry_time,
                    source="IMD Live",
                    instructions=instructions,
                    is_mock=False,
                )
                live_alerts.append(alert)

            return live_alerts

    except Exception as exc:
        logger.error("fetch_live_imd_alerts() crashed: %s", exc, exc_info=True)
        return []




def _replace_live_alerts(live_alerts: List[Alert]) -> None:
    """
    Swap out the previous batch of "IMD Live" alerts for a fresh one.

    The old code only ever did `_store.clear()`, which wipes the in-memory
    dict but leaves every previously-inserted row sitting in Supabase —
    `get_active_alerts()` reads from Supabase first, filtering only by
    `expiry_time` (fixed at issue_time + 48h). That's why old, possibly
    mislabeled alerts could keep showing up for up to two days after IMD
    itself had already moved on: nothing ever told Supabase they were stale.

    This deletes the previous live batch (mock alerts are left untouched)
    from both places before inserting the new one, so what's "active" always
    matches exactly what the feed says right now.
    """
    stale_ids = [aid for aid, a in _store.items() if a.source == "IMD Live"]
    for aid in stale_ids:
        del _store[aid]

    try:
        supabase = get_supabase_client()
        supabase.table("alerts").delete().eq("source", "IMD Live").execute()
    except Exception as exc:
        logger.warning("Supabase stale live-alert cleanup failed: %s", exc)

    for a in live_alerts:
        add_alert(a)


def fetch_and_store_alerts() -> List[Alert]:
    """
    Attempts to fetch live IMD alerts. If found, replaces the previous live
    batch entirely (see _replace_live_alerts) so stale/rotated-out alerts
    never linger. If the feed is empty or unreachable or all items are expired,
    seeds fallback mock alerts if store has no active items.
    """
    logger.info("=== fetch_and_store_alerts() called ===")
    live_alerts = fetch_live_imd_alerts()
    now = _now_utc()
    if live_alerts:
        # Items currently on the live IMD RSS channel are active official bulletins.
        # Ensure their expiry_time is in the future while active on feed.
        for a in live_alerts:
            if a.expiry_time <= now:
                a.expiry_time = now + timedelta(hours=24)
        logger.info("Storing %d live IMD alert(s) from official feed.", len(live_alerts))
        _replace_live_alerts(live_alerts)
    else:
        logger.info(
            "No live IMD alerts currently available (feed empty or unreachable). "
            "Checking fallback alert store."
        )
        if not _store or all(a.expiry_time <= now for a in _store.values()):
            _seed_mock_alerts()

    return list(_store.values())


# Fetch live alerts on startup
fetch_and_store_alerts()