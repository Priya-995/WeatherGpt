"""
IMD District GIS Ingest Service.

Fetches official district-wise warning GeoJSON from IMD GeoServer WFS API:
  https://reactjs.imd.gov.in/geoserver/wfs?service=WFS&version=1.1.0&request=GetFeature&typename=imd:district_warnings_india&srsname=EPSG:4326&outputFormat=application/json

Parsed fields:
- District: District name (e.g. 'BELGAUM', 'BIJAPUR', 'LUCKNOW', 'THANE')
- sub: Subdivision name
- Day_1: Weather warning code(s) (e.g. '4,8', '2,4', '16')
- Day1_Color: Severity level (2: Extreme/Red, 3: Severe/Orange, 4: Moderate/Yellow)
- lat, lon: District centroid coordinates
- geometry: Polygon / MultiPolygon boundaries
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import httpx

from app.schemas.alert import Alert, AlertSeverity, AlertType
from app.services.imd_subdivision_ingest import CATEGORY_MAP, COLOR_SEVERITY_MAP, parse_geometry_polygons

logger = logging.getLogger(__name__)

IMD_DISTRICT_GIS_WFS_URL = (
    "https://reactjs.imd.gov.in/geoserver/wfs"
    "?service=WFS&version=1.1.0&request=GetFeature"
    "&typename=imd:district_warnings_india&srsname=EPSG:4326&outputFormat=application/json"
)


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


async def fetch_imd_district_alerts() -> List[Alert]:
    """
    Fetch and parse live district warning GeoJSON from IMD GeoServer WFS API.
    Only returns active warnings (Yellow, Orange, Red status).
    """
    alerts: List[Alert] = []
    now = _now_utc()
    expiry = now + timedelta(hours=24)

    try:
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            resp = await client.get(IMD_DISTRICT_GIS_WFS_URL)
            if resp.status_code != 200:
                logger.warning("IMD District GeoServer WFS endpoint returned HTTP %d", resp.status_code)
                return []

            data = resp.json()
            features = data.get("features", [])
            logger.info("Fetched %d district features from IMD GeoServer.", len(features))

            for feat in features:
                props = feat.get("properties", {})
                district_raw = props.get("District", "").strip()
                if not district_raw:
                    continue

                # Day_1 warning codes e.g. "4,8" or "1"
                raw_day1 = str(props.get("Day_1", "1"))
                warning_codes = [c.strip() for c in raw_day1.split(",") if c.strip()]

                active_codes = [c for c in warning_codes if c != "1"]
                if not active_codes:
                    # District has no active warning today
                    continue

                raw_color = props.get("Day1_Color")
                try:
                    color_level = int(raw_color) if raw_color is not None else 4
                except (ValueError, TypeError):
                    color_level = 4

                severity = COLOR_SEVERITY_MAP.get(color_level, AlertSeverity.MODERATE)

                category_names: List[str] = []
                primary_alert_type = AlertType.OTHER

                for code in active_codes:
                    if code in CATEGORY_MAP:
                        a_type, cat_name = CATEGORY_MAP[code]
                        category_names.append(cat_name)
                        if primary_alert_type == AlertType.OTHER and a_type != AlertType.OTHER:
                            primary_alert_type = a_type

                if not category_names:
                    category_names = ["Weather Warning"]

                warning_desc = ", ".join(list(dict.fromkeys(category_names)))

                # Coordinates / centroids
                lat_val = props.get("lat")
                lon_val = props.get("lon")
                affected_lat = float(lat_val) if lat_val is not None else None
                affected_lon = float(lon_val) if lon_val is not None else None

                subdiv_name = props.get("sub", "").strip()
                state_name = props.get("state", "").strip()
                text_info = props.get("Day1_text", "").strip()

                district_title = district_raw.title()
                area_description = f"District {district_title}"
                if subdiv_name:
                    area_description += f", {subdiv_name}"

                instructions = (
                    f"Official IMD Warning for District {district_title}: {warning_desc}. "
                    + (f"Details: {text_info}." if text_info else "Follow local authorities and take necessary safety precautions.")
                )

                geometry = feat.get("geometry")
                polygons = parse_geometry_polygons(geometry)

                dist_clean = district_raw.lower().replace(" ", "-").replace("&", "and")
                alert_id = f"IMD-DIST-{dist_clean}-{now.strftime('%Y%m%d')}"

                alert = Alert(
                    id=alert_id,
                    alert_type=primary_alert_type,
                    severity=severity,
                    affected_location=district_title,
                    affected_lat=affected_lat,
                    affected_lon=affected_lon,
                    affected_radius_km=100.0,
                    issue_time=now,
                    expiry_time=expiry,
                    source="IMD District GIS",
                    instructions=instructions,
                    is_mock=False,
                    area_desc=area_description,
                    polygons=polygons,
                )
                alerts.append(alert)

    except Exception as exc:
        logger.error("Error fetching IMD District GIS warnings: %s", exc, exc_info=True)

    logger.info("Successfully ingested %d active IMD District GIS alert(s).", len(alerts))
    return alerts
