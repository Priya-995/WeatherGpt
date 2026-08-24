"""
Pydantic schemas for weather alerts.

Field names and semantics are modelled after real IMD (India Meteorological
Department) alert bulletins so the service is straightforward to swap from
mock data to the live feed in Section 8.

IMD severity levels (official terminology):
  "green"   → no warning / watch
  "yellow"  → watch (be aware)
  "orange"  → alert (be prepared)
  "red"     → warning (take action)

We also normalise these into a generic 4-level scale used by the risk engine:
  yellow  → minor
  orange  → moderate
  red     → severe
  (extreme is reserved for multi-red compound events, not currently issued by IMD)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """
    Normalised severity scale.
    Maps to risk_engine._ALERT_LEVEL_MAP keys.
    """
    MINOR    = "minor"     # IMD yellow
    MODERATE = "moderate"  # IMD orange
    SEVERE   = "severe"    # IMD red
    EXTREME  = "extreme"   # compound / multi-hazard (reserved)


class AlertType(str, Enum):
    """WMO / IMD hazard type codes (subset used in India)."""
    THUNDERSTORM   = "thunderstorm"
    HEAVY_RAIN     = "heavy_rain"
    VERY_HEAVY_RAIN = "very_heavy_rain"
    CYCLONE        = "cyclone"
    HEAT_WAVE      = "heat_wave"
    COLD_WAVE      = "cold_wave"
    FLOOD          = "flood"
    STRONG_WIND    = "strong_wind"
    DENSE_FOG      = "dense_fog"
    HAILSTORM      = "hailstorm"
    DUST_STORM     = "dust_storm"
    OTHER          = "other"


class Alert(BaseModel):
    """
    A single weather alert / official warning.

    This schema matches the shape of real IMD alert bulletins.
    ─────────────────────────────────────────────────────────
    When swapping in the live IMD feed (Section 8 / Supabase),
    map the API response fields to these names.  The IMD TIGGE /
    DHM XML feed uses tags that map as follows:
      <identifier>   → id
      <event>        → alert_type
      <severity>     → severity (normalise yellow/orange/red)
      <area>/<areaDesc> → affected_location
      <sent>         → issue_time
      <expires>      → expiry_time
      <description>  → instructions
    ─────────────────────────────────────────────────────────
    """
    id: str = Field(..., description="Unique alert identifier (UUID or IMD bulletin ID)")
    alert_type: AlertType = Field(..., description="Hazard category")
    severity: AlertSeverity = Field(..., description="Normalised severity level")
    affected_location: str = Field(
        ..., description="Human-readable location name (district, state, or region)"
    )
    affected_lat: Optional[float] = Field(
        None, description="Approximate centroid latitude of the affected area"
    )
    affected_lon: Optional[float] = Field(
        None, description="Approximate centroid longitude of the affected area"
    )
    affected_radius_km: Optional[float] = Field(
        None, description="Radius in km around the centroid covered by this alert"
    )
    issue_time: datetime = Field(..., description="When the alert was issued (UTC)")
    expiry_time: datetime = Field(..., description="When the alert expires (UTC)")
    source: str = Field(
        "IMD",
        description="Issuing authority (e.g. 'IMD', 'NDMA', 'mock')"
    )
    instructions: str = Field(
        ...,
        description="Plain-English public instructions from the issuing authority"
    )
    is_mock: bool = Field(
        False,
        description="True if this is synthetic/mock data (not a real official alert)"
    )


class AlertStoreResponse(BaseModel):
    """Response envelope for GET /api/alerts."""
    active_count: int = Field(..., description="Number of currently active (non-expired) alerts")
    alerts: List[Alert] = Field(..., description="List of active Alert objects")
