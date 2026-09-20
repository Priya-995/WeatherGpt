import asyncio
from datetime import datetime, timezone
import logging
import re
from typing import Optional
import defusedxml.ElementTree as ET
from shapely.geometry import Point, Polygon

from app.core.cache import ServiceCache
from app.core.errors import UpstreamError
from app.core.http import get_http_client
from app.schemas.alerts import Alert, AlertArea, AlertMatch
from app.schemas.geo import Place

logger = logging.getLogger(__name__)

feed_cache = ServiceCache(maxsize=10, ttl=300)      # 5 minutes for RSS feed
cap_cache = ServiceCache(maxsize=500, ttl=21600)    # 6 hours for individual CAP XML

IMD_RSS_URL = "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml"


def _get_local_text(element, name: str) -> Optional[str]:
    if element is None:
        return None
    for child in element:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == name:
            return child.text
    return None


def _findall_local(element, name: str) -> list:
    if element is None:
        return []
    res = []
    for child in element:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == name:
            res.append(child)
    return res


def _parse_cap_datetime(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(val.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


async def fetch_feed() -> list[str]:
    cached_links = feed_cache.get("rss_links")
    if cached_links is not None:
        logger.debug("Cache hit for IMD RSS feed")
        return cached_links

    client = get_http_client()
    try:
        response = await client.get(IMD_RSS_URL)
        if response.status_code >= 400:
            raise UpstreamError(service="IMD CAP Feed", status_code=response.status_code)
        content = response.content
    except Exception as exc:
        if isinstance(exc, UpstreamError):
            raise exc
        raise UpstreamError(service="IMD CAP Feed", status_code=502, message=str(exc)) from exc

    try:
        root = ET.fromstring(content)
    except Exception as exc:
        raise UpstreamError(service="IMD CAP Feed", status_code=502, message="Malformed RSS XML") from exc

    channel = _findall_local(root, "channel")
    channel_elem = channel[0] if channel else root
    items = _findall_local(channel_elem, "item")

    links = []
    for item in items:
        link = _get_local_text(item, "link")
        if link and link.strip():
            links.append(link.strip())

    feed_cache.set("rss_links", links)
    return links


def parse_cap_xml(content: bytes, link: Optional[str] = None) -> Alert:
    root = ET.fromstring(content)

    identifier = _get_local_text(root, "identifier") or ""
    sender = _get_local_text(root, "sender") or ""
    sent_str = _get_local_text(root, "sent")
    sent = _parse_cap_datetime(sent_str) or datetime.now(timezone.utc)

    status = _get_local_text(root, "status") or "Actual"
    msg_type = _get_local_text(root, "msgType") or "Alert"
    scope = _get_local_text(root, "scope") or "Public"
    references = _get_local_text(root, "references")

    info_elems = _findall_local(root, "info")
    info = info_elems[0] if info_elems else None

    category = _get_local_text(info, "category") if info is not None else "Met"
    event = _get_local_text(info, "event") if info is not None else "Unknown"
    urgency = _get_local_text(info, "urgency") if info is not None else "Unknown"
    severity = _get_local_text(info, "severity") if info is not None else "Unknown"
    certainty = _get_local_text(info, "certainty") if info is not None else "Unknown"

    effective = _parse_cap_datetime(_get_local_text(info, "effective")) if info is not None else None
    onset = _parse_cap_datetime(_get_local_text(info, "onset")) if info is not None else None
    expires = _parse_cap_datetime(_get_local_text(info, "expires")) if info is not None else None

    headline = _get_local_text(info, "headline") if info is not None else None
    description = _get_local_text(info, "description") if info is not None else None
    instruction = _get_local_text(info, "instruction") if info is not None else None

    areas = []
    if info is not None:
        area_elems = _findall_local(info, "area")
        for area_elem in area_elems:
            area_desc = _get_local_text(area_elem, "areaDesc") or ""
            polygon_str = _get_local_text(area_elem, "polygon")

            polygons = []
            if polygon_str and polygon_str.strip():
                pairs = polygon_str.strip().split()
                coords = []
                for p in pairs:
                    parts = p.split(",")
                    if len(parts) == 2:
                        try:
                            lat = float(parts[0])
                            lon = float(parts[1])
                            coords.append((lat, lon))
                        except ValueError:
                            pass
                if coords:
                    polygons.append(coords)

            circle_str = _get_local_text(area_elem, "circle")
            circles = [circle_str] if circle_str else []

            areas.append(AlertArea(area_desc=area_desc, polygons=polygons, circles=circles))

    return Alert(
        identifier=identifier,
        sender=sender,
        sent=sent,
        status=status,
        msg_type=msg_type,
        scope=scope,
        event=event,
        category=category,
        urgency=urgency,
        severity=severity,
        certainty=certainty,
        effective=effective,
        onset=onset,
        expires=expires,
        headline=headline,
        description=description,
        instruction=instruction,
        link=link,
        areas=areas,
        references=references,
        source="IMD"
    )


async def fetch_cap(url: str) -> Alert:
    cached_alert = cap_cache.get(url)
    if cached_alert is not None:
        logger.debug(f"Cache hit for CAP document: {url}")
        return cached_alert

    client = get_http_client()
    response = await client.get(url)
    if response.status_code >= 400:
        raise UpstreamError(service="IMD CAP Document", status_code=response.status_code)

    alert = parse_cap_xml(response.content, link=url)
    cap_cache.set(url, alert)
    return alert


async def get_current_alerts() -> tuple[list[Alert], int]:
    links = await fetch_feed()
    if not links:
        return [], 0

    sem = asyncio.Semaphore(5)

    async def _fetch_one(link: str) -> Optional[Alert]:
        async with sem:
            try:
                return await fetch_cap(link)
            except Exception as exc:
                logger.warning(f"Failed to fetch CAP document at {link}: {exc}")
                return None

    raw_results = await asyncio.gather(*[_fetch_one(link) for link in links])

    valid_alerts: list[Alert] = []
    skipped_count = 0

    for res in raw_results:
        if res is None:
            skipped_count += 1
        else:
            valid_alerts.append(res)

    superseded_ids = set()
    for alert in valid_alerts:
        if alert.references:
            for ref_part in re.split(r"[\s,]+", alert.references):
                if not ref_part:
                    continue
                tokens = ref_part.split(",")
                ref_id = tokens[1] if len(tokens) >= 2 else tokens[0]
                superseded_ids.add(ref_id)
        if alert.msg_type == "Cancel":
            superseded_ids.add(alert.identifier)

    now_utc = datetime.now(timezone.utc)
    active_alerts: list[Alert] = []

    for alert in valid_alerts:
        if alert.status != "Actual":
            skipped_count += 1
            logger.debug(f"Skipping alert {alert.identifier}: status={alert.status}")
            continue

        if alert.identifier in superseded_ids:
            skipped_count += 1
            logger.debug(f"Skipping alert {alert.identifier}: cancelled/superseded")
            continue

        if alert.expires and alert.expires < now_utc:
            skipped_count += 1
            logger.debug(f"Skipping alert {alert.identifier}: expired at {alert.expires}")
            continue

        active_alerts.append(alert)

    return active_alerts, skipped_count


def _normalize_name(name: str) -> str:
    return re.sub(r"[^\w\s]", "", name).strip().lower()


def match_location(
    alerts: list[Alert],
    lat: float,
    lon: float,
    place: Optional[Place] = None
) -> list[AlertMatch]:
    # NOTE: Shapely Point takes (longitude, latitude)
    point = Point(lon, lat)
    matches: list[AlertMatch] = []

    for alert in alerts:
        matched = False

        # a) Polygon Match
        for area in alert.areas:
            for poly_coords in area.polygons:
                if len(poly_coords) < 3:
                    continue
                shapely_coords = [(p[1], p[0]) for p in poly_coords]
                try:
                    poly = Polygon(shapely_coords)
                    if poly.contains(point) or poly.touches(point):
                        matched_desc = area.area_desc or "polygon"
                        matches.append(
                            AlertMatch(
                                alert=alert,
                                match_method="polygon",
                                matched_on=f"Polygon in {matched_desc}"
                            )
                        )
                        matched = True
                        break
                except Exception as exc:
                    logger.warning(f"Invalid polygon in alert {alert.identifier}: {exc}")
            if matched:
                break

        if matched:
            continue

        # b) District Match (admin2)
        if place and place.admin2:
            dist_norm = _normalize_name(place.admin2)
            for area in alert.areas:
                area_desc_norm = _normalize_name(area.area_desc)
                headline_norm = _normalize_name(alert.headline or "")
                desc_norm = _normalize_name(alert.description or "")

                if (dist_norm in area_desc_norm) or (dist_norm in headline_norm) or (dist_norm in desc_norm):
                    matches.append(
                        AlertMatch(
                            alert=alert,
                            match_method="district",
                            matched_on=place.admin2
                        )
                    )
                    matched = True
                    break

        if matched:
            continue

        # c) State Fallback Match (admin1)
        if place and place.admin1:
            state_norm = _normalize_name(place.admin1)
            for area in alert.areas:
                area_desc_norm = _normalize_name(area.area_desc)
                headline_norm = _normalize_name(alert.headline or "")
                desc_norm = _normalize_name(alert.description or "")

                if (state_norm in area_desc_norm) or (state_norm in headline_norm) or (state_norm in desc_norm):
                    matches.append(
                        AlertMatch(
                            alert=alert,
                            match_method="state",
                            matched_on=place.admin1
                        )
                    )
                    matched = True
                    break

    return matches
