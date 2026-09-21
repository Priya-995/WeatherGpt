"""
CAP Ingest Service — Live IMD CAP RSS Feed Ingest & XML Parser.

Fetches official WMO / IMD CAP RSS feeds:
  https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml

Features:
- Async RSS & CAP XML fetching with caching per URL.
- Ignore items older than 3 days.
- Parse CAP fields (status, msgType, references, info, event, severity, expires, polygon, areaDesc).
- Filter out status != "Actual".
- Handle Update / Cancel msgType references to drop superseded alerts.
- Map CAP severity: Extreme -> EXTREME, Severe -> SEVERE, Moderate -> MODERATE, Minor/Unknown -> MINOR.
- Fallback expiry_time: sent + 24h if cap:expires is missing.
- Point-in-polygon ray casting algorithm for coordinate queries.
- Uttar Pradesh region matcher ("uttar pradesh", "east uttar pradesh", "west uttar pradesh").
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Set, Tuple

import httpx

from app.schemas.alert import Alert, AlertSeverity, AlertType

logger = logging.getLogger(__name__)

IMD_CAP_RSS_URL = "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml"

# In-memory cache for parsed CAP XML files by URL (URL -> List[Alert])
_cap_url_cache: Dict[str, List[Alert]] = {}


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        clean_str = dt_str.strip()
        dt = datetime.fromisoformat(clean_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _get_local_text(elem: ET.Element, name: str) -> str:
    """Helper to get child text ignoring XML namespace prefixes."""
    for child in elem:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == name:
            return child.text or ""
    return ""


def _get_local_children(elem: ET.Element, name: str) -> List[ET.Element]:
    """Helper to find all child elements matching tag name ignoring namespace."""
    res = []
    for child in elem:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == name:
            res.append(child)
    return res


def map_cap_severity(cap_sev: str) -> AlertSeverity:
    """Map CAP severity string to AlertSeverity schema enum."""
    sev_lower = (cap_sev or "").strip().lower()
    if sev_lower == "extreme":
        return AlertSeverity.EXTREME
    elif sev_lower == "severe":
        return AlertSeverity.SEVERE
    elif sev_lower == "moderate":
        return AlertSeverity.MODERATE
    elif sev_lower == "minor":
        return AlertSeverity.MINOR
    else:
        # Unknown -> Minor
        return AlertSeverity.MINOR


def map_cap_event_type(event_text: str, headline: str = "", description: str = "") -> AlertType:
    """Infer AlertType enum from event text, headline, or description."""
    text = f"{event_text} {headline} {description}".lower()
    if "extremely heavy" in text or "very heavy rain" in text:
        return AlertType.VERY_HEAVY_RAIN
    if "heavy rain" in text or "rainfall" in text:
        return AlertType.HEAVY_RAIN
    if "thunderstorm" in text or "lightning" in text or "squall" in text:
        return AlertType.THUNDERSTORM
    if "cyclone" in text or "depression" in text:
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
    if "hail" in text or "hailstorm" in text:
        return AlertType.HAILSTORM
    if "dust" in text:
        return AlertType.DUST_STORM
    return AlertType.OTHER


def parse_polygon_string(poly_str: str) -> List[Tuple[float, float]]:
    """
    Parse a CAP polygon string: "lat,lon lat,lon lat,lon ..."
    Returns a list of (lat, lon) float tuples.
    """
    if not poly_str or not poly_str.strip():
        return []
    coords: List[Tuple[float, float]] = []
    tokens = poly_str.strip().split()
    for token in tokens:
        parts = token.split(",")
        if len(parts) == 2:
            try:
                lat = float(parts[0])
                lon = float(parts[1])
                coords.append((lat, lon))
            except ValueError:
                continue
    return coords


def point_in_polygon(lat: float, lon: float, polygon: List[Tuple[float, float]]) -> bool:
    """
    Pure Python ray casting algorithm to check if point (lat, lon) is inside polygon.
    Polygon is a list of (lat, lon) coordinate tuples.
    """
    n = len(polygon)
    if n < 3:
        return False
    inside = False
    p1_lat, p1_lon = polygon[0]
    for i in range(1, n + 1):
        p2_lat, p2_lon = polygon[i % n]
        if lon > min(p1_lon, p2_lon):
            if lon <= max(p1_lon, p2_lon):
                if lat <= max(p1_lat, p2_lat):
                    if p1_lon != p2_lon:
                        lat_inters = (lon - p1_lon) * (p2_lat - p1_lat) / (p2_lon - p1_lon) + p1_lat
                    else:
                        lat_inters = p1_lat
                    if p1_lat == p2_lat or lat <= lat_inters:
                        inside = not inside
        p1_lat, p1_lon = p2_lat, p2_lon
    return inside


def is_uttar_pradesh_alert(alert: Alert) -> bool:
    """
    Check if an alert applies to Uttar Pradesh.
    Returns True if areaDesc or affected_location contains "uttar pradesh" (case-insensitive).
    This matches "Uttar Pradesh", "East Uttar Pradesh", "West Uttar Pradesh", etc.
    """
    location = (alert.affected_location or "").lower()
    area_desc = (alert.area_desc or "").lower()
    return "uttar pradesh" in location or "uttar pradesh" in area_desc


def parse_cap_xml(xml_content: str, source_url: str = "") -> Tuple[List[Alert], Set[str]]:
    """
    Parse a CAP XML bulletin string (urn:oasis:names:tc:emergency:cap:1.2).

    Returns:
      (alerts: List[Alert], cancelled_referenced_ids: Set[str])
    """
    try:
        root = ET.fromstring(xml_content)
    except Exception as exc:
        logger.warning("Failed to parse CAP XML from %s: %s", source_url, exc)
        return [], set()

    status = _get_local_text(root, "status")
    if status.strip() != "Actual":
        logger.debug("Skipping CAP XML %s: status=%s (not Actual)", source_url, status)
        return [], set()

    identifier = _get_local_text(root, "identifier") or source_url or str(uuid.uuid4())
    msg_type = _get_local_text(root, "msgType")
    sent_str = _get_local_text(root, "sent")
    issue_time = _parse_iso_datetime(sent_str) or _now_utc()

    cancelled_referenced_ids: Set[str] = set()
    references_str = _get_local_text(root, "references")
    if references_str and msg_type in ("Update", "Cancel"):
        # Format of references: "sender,identifier,sent sender,identifier,sent ..."
        # Extract referenced identifiers
        for ref_item in references_str.split():
            ref_parts = ref_item.split(",")
            if len(ref_parts) >= 2:
                ref_id = ref_parts[1].strip()
                if ref_id:
                    cancelled_referenced_ids.add(ref_id)

    info_elems = _get_local_children(root, "info")
    if not info_elems:
        return [], cancelled_referenced_ids

    alerts: List[Alert] = []

    for idx, info in enumerate(info_elems):
        event = _get_local_text(info, "event")
        severity_str = _get_local_text(info, "severity")
        severity = map_cap_severity(severity_str)
        expires_str = _get_local_text(info, "expires")
        expiry_time = _parse_iso_datetime(expires_str)
        if not expiry_time:
            expiry_time = issue_time + timedelta(hours=24)

        headline = _get_local_text(info, "headline")
        description = _get_local_text(info, "description")
        instruction = _get_local_text(info, "instruction") or description or "Follow official IMD directives."

        alert_type = map_cap_event_type(event, headline, description)

        area_elems = _get_local_children(info, "area")
        area_descs: List[str] = []
        polygons: List[List[Tuple[float, float]]] = []

        all_lats: List[float] = []
        all_lons: List[float] = []

        for area in area_elems:
            a_desc = _get_local_text(area, "areaDesc")
            if a_desc:
                area_descs.append(a_desc.strip())
            poly_str = _get_local_text(area, "polygon")
            if poly_str:
                poly = parse_polygon_string(poly_str)
                if poly:
                    polygons.append(poly)
                    for plat, plon in poly:
                        all_lats.append(plat)
                        all_lons.append(plon)

        location_str = ", ".join(area_descs) if area_descs else (headline or "India")
        full_area_desc = "; ".join(area_descs) if area_descs else None

        affected_lat: Optional[float] = None
        affected_lon: Optional[float] = None
        affected_radius_km: Optional[float] = None

        if all_lats and all_lons:
            affected_lat = sum(all_lats) / len(all_lats)
            affected_lon = sum(all_lons) / len(all_lons)
            # Estimate approximate radius in km from centroid to farthest polygon point
            max_d2 = 0.0
            for plat, plon in zip(all_lats, all_lons):
                dlat = (plat - affected_lat) * 111.0
                dlon = (plon - affected_lon) * 111.0 * 0.85
                d2 = dlat * dlat + dlon * dlon
                if d2 > max_d2:
                    max_d2 = d2
            affected_radius_km = round((max_d2 ** 0.5) + 20.0, 1)

        alert_id = f"{identifier}-{idx}" if len(info_elems) > 1 else identifier

        alert = Alert(
            id=alert_id,
            alert_type=alert_type,
            severity=severity,
            affected_location=location_str,
            affected_lat=affected_lat,
            affected_lon=affected_lon,
            affected_radius_km=affected_radius_km,
            issue_time=issue_time,
            expiry_time=expiry_time,
            source="IMD CAP Live",
            instructions=instruction,
            is_mock=False,
            area_desc=full_area_desc,
            polygons=polygons,
        )
        alerts.append(alert)

    return alerts, cancelled_referenced_ids


async def fetch_cap_xml(url: str, client: httpx.AsyncClient) -> Tuple[List[Alert], Set[str]]:
    """Fetch and parse a single CAP XML file by URL using cache if available."""
    if url in _cap_url_cache:
        logger.debug("Cache hit for CAP XML URL: %s", url)
        return _cap_url_cache[url], set()

    try:
        resp = await client.get(url, timeout=6.0)
        if resp.status_code != 200:
            logger.warning("HTTP %d fetching CAP XML from %s", resp.status_code, url)
            return [], set()

        alerts, cancelled_ids = parse_cap_xml(resp.text, source_url=url)
        if alerts:
            _cap_url_cache[url] = alerts
        return alerts, cancelled_ids
    except Exception as exc:
        logger.warning("Failed fetching CAP XML from %s: %s", url, exc)
        return [], set()


async def fetch_and_parse_cap_feed(client: Optional[httpx.AsyncClient] = None) -> List[Alert]:
    """
    Fetch the main RSS feed, parse item CAP XMLs concurrently, and return active parsed alerts.
    Ignores RSS items / CAP bulletins older than 3 days.
    Filter out cancelled / updated bulletins.
    """
    logger.info("=== Fetching IMD CAP RSS Feed ===")
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=8.0)
        close_client = True

    try:
        resp = await client.get(IMD_CAP_RSS_URL)
        if resp.status_code != 200:
            logger.warning("IMD RSS feed returned HTTP %s", resp.status_code)
            return []

        try:
            root = ET.fromstring(resp.text)
        except Exception as exc:
            logger.error("Failed to parse RSS XML: %s", exc)
            return []

        items = _get_local_children(_get_local_children(root, "channel")[0] if _get_local_children(root, "channel") else root, "item")
        if not items:
            items = root.findall(".//item")

        logger.info("IMD RSS feed returned %d raw items.", len(items))
        if not items:
            return []

        now = _now_utc()
        three_days_ago = now - timedelta(days=3)

        urls_to_fetch: List[str] = []
        for item in items:
            link = _get_local_text(item, "link").strip()
            pub_date_str = _get_local_text(item, "pubDate").strip()

            # Ignore items older than 3 days
            if pub_date_str:
                try:
                    dt = parsedate_to_datetime(pub_date_str)
                    if dt:
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        if dt < three_days_ago:
                            logger.debug("Skipping RSS item published >3 days ago: %s (%s)", link, pub_date_str)
                            continue
                except Exception:
                    pass

            if link and link not in urls_to_fetch:
                urls_to_fetch.append(link)

        if not urls_to_fetch:
            return []

        logger.info("Fetching %d CAP XML files concurrently...", len(urls_to_fetch))
        tasks = [fetch_cap_xml(url, client) for url in urls_to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_alerts: List[Alert] = []
        all_cancelled_ids: Set[str] = set()

        for res in results:
            if isinstance(res, tuple):
                alerts, cancelled_ids = res
                all_alerts.extend(alerts)
                all_cancelled_ids.update(cancelled_ids)

        # Drop alerts cancelled or replaced via Update/Cancel references
        if all_cancelled_ids:
            logger.info("Superseding %d cancelled/updated alert IDs: %r", len(all_cancelled_ids), all_cancelled_ids)
            all_alerts = [a for a in all_alerts if a.id not in all_cancelled_ids]

        # Drop expired alerts based on real expiry_time
        active_alerts = [a for a in all_alerts if a.expiry_time > now]

        logger.info("Successfully ingested %d active IMD CAP alert(s).", len(active_alerts))
        return active_alerts

    except Exception as exc:
        logger.error("Error in fetch_and_parse_cap_feed: %s", exc, exc_info=True)
        return []
    finally:
        if close_client:
            await client.aclose()
