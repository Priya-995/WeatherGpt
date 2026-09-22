"""
IMD Subdivision GIS Ingest Service.

Fetches official subdivision-wise warning GeoJSON from IMD GeoServer WFS API:
  https://reactjs.imd.gov.in/geoserver/wfs?service=WFS&version=1.1.0&request=GetFeature&typename=imd:subdiv_warnings_now&srsname=EPSG:4326&outputFormat=application/json

Parsed fields:
- SUBDIV: Subdivision name (e.g. 'East Uttar Pradesh', 'Konkan & Goa', 'Odisha')
- Day_1: Weather warning code (e.g. '42' = Thunderstorm & Lightning, '16' = Very Heavy Rain)
- Day1_Color: Severity level (1: Green/No Warning, 2: Yellow/Watch, 3: Orange/Alert, 4: Red/Warning)
- lat, lon: Subdivision centroid
- geometry: MultiPolygon geometry for coordinate filtering
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import httpx

from app.schemas.alert import Alert, AlertSeverity, AlertType

logger = logging.getLogger(__name__)

IMD_GIS_WFS_URL = (
    "https://reactjs.imd.gov.in/geoserver/wfs"
    "?service=WFS&version=1.1.0&request=GetFeature"
    "&typename=imd:subdiv_warnings_now&srsname=EPSG:4326&outputFormat=application/json"
)

# IMD Warning Category Codes mapping -> (AlertType, Description)
CATEGORY_MAP: Dict[str, Tuple[AlertType, str]] = {
    "1": (AlertType.OTHER, "No Warning"),
    "2": (AlertType.HEAVY_RAIN, "Heavy Rain"),
    "3": (AlertType.OTHER, "Heavy Snow"),
    "4": (AlertType.THUNDERSTORM, "Thunderstorm & Lightning"),
    "5": (AlertType.HAILSTORM, "Hailstorm"),
    "6": (AlertType.DUST_STORM, "Dust Storm"),
    "7": (AlertType.DUST_STORM, "Dust Raising Winds"),
    "8": (AlertType.STRONG_WIND, "Strong Surface Winds"),
    "9": (AlertType.HEAT_WAVE, "Heat Wave"),
    "91": (AlertType.HEAT_WAVE, "Severe Heat Wave"),
    "10": (AlertType.HEAT_WAVE, "Hot Day"),
    "11": (AlertType.HEAT_WAVE, "Warm Night"),
    "12": (AlertType.COLD_WAVE, "Cold Wave"),
    "121": (AlertType.COLD_WAVE, "Severe Cold Wave"),
    "13": (AlertType.COLD_WAVE, "Cold Day"),
    "131": (AlertType.COLD_WAVE, "Severe Cold Day"),
    "14": (AlertType.OTHER, "Ground Frost"),
    "15": (AlertType.DENSE_FOG, "Fog"),
    "151": (AlertType.DENSE_FOG, "Dense Fog"),
    "152": (AlertType.DENSE_FOG, "Very Dense Fog"),
    "16": (AlertType.VERY_HEAVY_RAIN, "Very Heavy Rain"),
    "17": (AlertType.VERY_HEAVY_RAIN, "Extremely Heavy Rain"),
    "18": (AlertType.HEAT_WAVE, "Hot and Humid"),
    "41": (AlertType.THUNDERSTORM, "Thunderstorm & Lightning"),
    "42": (AlertType.THUNDERSTORM, "Thunderstorm & Lightning"),
    "43": (AlertType.THUNDERSTORM, "Thunderstorm & Lightning"),
    "44": (AlertType.THUNDERSTORM, "Thunderstorm & Lightning"),
    "45": (AlertType.THUNDERSTORM, "Thunderstorm & Lightning"),
    "46": (AlertType.THUNDERSTORM, "Thunderstorm & Lightning"),
}

# Color level mapping -> AlertSeverity
# IMD WFS Color mapping: 2 = Red (Extreme), 3 = Orange (Severe), 4 = Yellow (Moderate)
COLOR_SEVERITY_MAP: Dict[int, AlertSeverity] = {
    2: AlertSeverity.EXTREME,   # Red / Warning
    3: AlertSeverity.SEVERE,    # Orange / Alert
    4: AlertSeverity.MODERATE,  # Yellow / Watch
}


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def parse_geometry_polygons(geometry: Optional[dict]) -> List[List[Tuple[float, float]]]:
    """Convert GeoJSON Polygon/MultiPolygon to list of [(lat, lon)] coordinate rings."""
    if not geometry:
        return []

    polygons: List[List[Tuple[float, float]]] = []
    g_type = geometry.get("type", "")
    coords = geometry.get("coordinates", [])

    try:
        if g_type == "Polygon":
            for ring in coords:
                poly = [(float(pt[1]), float(pt[0])) for pt in ring if len(pt) >= 2]
                if poly:
                    polygons.append(poly)
        elif g_type == "MultiPolygon":
            for polygon_rings in coords:
                for ring in polygon_rings:
                    poly = [(float(pt[1]), float(pt[0])) for pt in ring if len(pt) >= 2]
                    if poly:
                        polygons.append(poly)
    except Exception as exc:
        logger.warning("Error parsing geometry coordinates: %s", exc)

    return polygons


async def fetch_imd_subdivision_alerts() -> List[Alert]:
    """
    Fetch and parse live subdivision warning GeoJSON from IMD GeoServer WFS API.
    Only returns active warnings (Yellow, Orange, Red status).
    """
    alerts: List[Alert] = []
    now = _now_utc()
    expiry = now + timedelta(hours=24)

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(IMD_GIS_WFS_URL)
            if resp.status_code != 200:
                logger.warning("IMD GeoServer WFS endpoint returned HTTP %d", resp.status_code)
                return []

            data = resp.json()
            features = data.get("features", [])
            logger.info("Fetched %d subdivision features from IMD GeoServer.", len(features))

            for feat in features:
                props = feat.get("properties", {})
                subdiv = props.get("SUBDIV", "").strip()
                if not subdiv:
                    continue

                # Day_1 codes can be comma separated string e.g. "42,01" or "1"
                raw_day1 = str(props.get("Day_1", "1"))
                warning_codes = [c.strip() for c in raw_day1.split(",") if c.strip()]

                # Filter out "1" (No Warning) codes
                active_codes = [c for c in warning_codes if c != "1"]
                if not active_codes:
                    # Subdivision has no active warning today
                    continue

                # Day1_Color indicates today's warning severity (2=Red/Extreme, 3=Orange/Severe, 4=Yellow/Moderate)
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

                # Additional district details if present
                dist_info = props.get("dist1", "").strip()
                instructions = (
                    f"Official IMD Warning for '{subdiv}': {warning_desc}. "
                    + (f"Affected districts/areas: {dist_info}." if dist_info else "Follow local IMD bulletins and take necessary safety precautions.")
                )

                geometry = feat.get("geometry")
                polygons = parse_geometry_polygons(geometry)

                # Construct unique ID for subdivision warning
                subdiv_clean = subdiv.lower().replace(" ", "-").replace("&", "and")
                alert_id = f"IMD-SUBDIV-{subdiv_clean}-{now.strftime('%Y%m%d')}"

                alert = Alert(
                    id=alert_id,
                    alert_type=primary_alert_type,
                    severity=severity,
                    affected_location=subdiv,
                    affected_lat=affected_lat,
                    affected_lon=affected_lon,
                    affected_radius_km=300.0,
                    issue_time=now,
                    expiry_time=expiry,
                    source="IMD Subdivision GIS",
                    instructions=instructions,
                    is_mock=False,
                    area_desc=f"{subdiv} Meteorological Subdivision",
                    polygons=polygons,
                )
                alerts.append(alert)

    except Exception as exc:
        logger.error("Error fetching IMD Subdivision GIS warnings: %s", exc, exc_info=True)

    logger.info("Successfully ingested %d active IMD Subdivision GIS alert(s).", len(alerts))
    return alerts
