"""
Advisory Engine — explicit rule-based recommendations.

Design contract
---------------
- Pure if/else logic. No ML, no probabilities, no model calls.
- Every rule is a named function with a docstring explaining the trigger condition.
- Rules are evaluated independently; multiple can fire simultaneously.
- Each AdvisoryItem records which conditions triggered it (triggered_by list)
  so any recommendation is fully auditable.

Contexts covered
----------------
  citizen   : general public / travel advisories
  farmer    : agricultural advisories (spraying, irrigation, harvest)
  heat      : heat-health advisories (hydration, outdoor work limits)

Future contexts (Section 7)
--------------------------
  alert     : official warning escalation advisories
"""

from __future__ import annotations

from typing import List, Optional

from app.schemas.risk import AdvisoryItem, AdvisoryResult, RiskLevel
from app.schemas.weather import WeatherResponse


# ---------------------------------------------------------------------------
# Helper — pull the dominant daily values for today and tomorrow
# ---------------------------------------------------------------------------

def _daily(weather: WeatherResponse, day: int = 0):
    """Return a simple namespace for a given forecast day (0 = today, 1 = tomorrow)."""
    d = weather.daily
    if not d or not getattr(d, "time", None):
        return {
            "date": "", "precip_sum": 0.0, "precip_prob": 0,
            "temp_max": 28.0, "temp_min": 20.0, "feels_max": 28.0, "feels_min": 20.0,
            "wind_max": 12.0, "gust_max": 15.0, "weather_code": 0
        }
    idx = min(day, max(0, len(d.time) - 1))

    def _val(arr, default=0.0):
        if arr and len(arr) > idx and arr[idx] is not None:
            return arr[idx]
        return default

    return {
        "date":          _val(d.time, ""),
        "precip_sum":    float(_val(d.precipitation_sum, 0.0)),
        "precip_prob":   int(_val(d.precipitation_probability_max, 0)),
        "temp_max":      float(_val(d.temperature_2m_max, 28.0)),
        "temp_min":      float(_val(d.temperature_2m_min, 20.0)),
        "feels_max":     float(_val(d.apparent_temperature_max, 28.0)),
        "feels_min":     float(_val(d.apparent_temperature_min, 20.0)),
        "wind_max":      float(_val(d.wind_speed_10m_max, 12.0)),
        "gust_max":      float(_val(d.wind_gusts_10m_max, 15.0)),
        "weather_code":  int(_val(d.weather_code, 0)),
    }


def _next_6h_precip_prob(weather: WeatherResponse) -> int:
    """Max precipitation probability across the next 6 hourly slots."""
    probs = [p for p in weather.hourly.precipitation_probability[:6] if p is not None]
    return max(probs) if probs else 0


# ---------------------------------------------------------------------------
# CITIZEN / TRAVEL rules
# ---------------------------------------------------------------------------

def _rule_avoid_travel_active_warning(
    weather: WeatherResponse, alert_data: Optional[dict]
) -> Optional[AdvisoryItem]:
    """Trigger: active official warning of any level + heavy rain expected."""
    if not alert_data:
        return None
    today = _daily(weather, 0)
    if today["precip_sum"] >= 7.5:
        return AdvisoryItem(
            context="citizen",
            severity="danger",
            title="Avoid Non-Essential Travel",
            message=(
                f"An official weather warning is active and heavy rain "
                f"({today['precip_sum']:.1f} mm) is forecast today. "
                "Avoid non-essential travel, especially at night or in low-lying areas. "
                "Keep emergency contacts handy."
            ),
            triggered_by=["active_official_warning", f"heavy_rain_{today['precip_sum']:.1f}mm"],
        )
    return None


def _rule_travel_rain_caution(weather: WeatherResponse) -> Optional[AdvisoryItem]:
    """Trigger: 24-hour rain > 7.5mm OR max precipitation probability > 70%."""
    today = _daily(weather, 0)
    if today["precip_sum"] >= 7.5 or today["precip_prob"] >= 70:
        return AdvisoryItem(
            context="citizen",
            severity="warning",
            title="Travel Caution — Wet Roads Expected",
            message=(
                f"Heavy or persistent rain expected today "
                f"({today['precip_sum']:.1f} mm, {today['precip_prob']}% probability). "
                "Allow extra travel time, check for road closures, and avoid driving through "
                "flooded roads. Keep your vehicle's lights on."
            ),
            triggered_by=[
                f"daily_precip_{today['precip_sum']:.1f}mm",
                f"precip_prob_{today['precip_prob']}pct",
            ],
        )
    return None


def _rule_strong_wind_caution(weather: WeatherResponse) -> Optional[AdvisoryItem]:
    """Trigger: daily max wind speed or gusts ≥ 50 km/h."""
    today = _daily(weather, 0)
    effective = max(today["wind_max"], today["gust_max"])
    if effective >= 50:
        severity = "danger" if effective >= 75 else "warning"
        return AdvisoryItem(
            context="citizen",
            severity=severity,
            title="Strong Wind Advisory",
            message=(
                f"Wind speeds up to {today['wind_max']:.0f} km/h with gusts to "
                f"{today['gust_max']:.0f} km/h are expected. "
                "Secure loose outdoor objects, avoid tall trees and scaffolding. "
                + ("Structural damage possible — stay indoors if possible." if effective >= 75 else "")
            ),
            triggered_by=[
                f"wind_max_{today['wind_max']:.0f}kmh",
                f"gust_max_{today['gust_max']:.0f}kmh",
            ],
        )
    return None


# ---------------------------------------------------------------------------
# FARMER rules
# ---------------------------------------------------------------------------

def _rule_postpone_spraying(weather: WeatherResponse) -> Optional[AdvisoryItem]:
    """
    Trigger: rain probability > 50% OR wind > 25 km/h within next 6 hours.
    Pesticide/herbicide spraying in these conditions is wasteful and hazardous.
    """
    prob_6h = _next_6h_precip_prob(weather)
    current_wind = weather.current.wind_speed_10m

    if prob_6h > 50 or current_wind > 25:
        reasons = []
        if prob_6h > 50:
            reasons.append(f"rain_prob_6h_{prob_6h}pct")
        if current_wind > 25:
            reasons.append(f"wind_{current_wind:.0f}kmh")

        return AdvisoryItem(
            context="farmer",
            severity="warning",
            title="Postpone Pesticide / Herbicide Spraying",
            message=(
                f"Conditions are unfavourable for spraying: "
                + (f"{prob_6h}% rain probability in the next 6 hours" if prob_6h > 50 else "")
                + (" and " if prob_6h > 50 and current_wind > 25 else "")
                + (f"wind speed {current_wind:.0f} km/h (drift risk)" if current_wind > 25 else "")
                + ". Spraying now will reduce efficacy and may contaminate water bodies. "
                "Wait for calm, dry conditions (wind < 15 km/h, rain probability < 30%)."
            ),
            triggered_by=reasons,
        )
    return None


def _rule_irrigation_not_needed(weather: WeatherResponse) -> Optional[AdvisoryItem]:
    """
    Trigger: next 24h cumulative rain ≥ 10 mm.
    Sufficient natural rainfall makes irrigation unnecessary and wasteful.
    """
    today = _daily(weather, 0)
    tomorrow = _daily(weather, 1)
    total_48h = today["precip_sum"] + tomorrow["precip_sum"]

    if today["precip_sum"] >= 10:
        return AdvisoryItem(
            context="farmer",
            severity="info",
            title="Irrigation Not Required Today",
            message=(
                f"Rainfall of {today['precip_sum']:.1f} mm is forecast today "
                f"(total next 48h: {total_48h:.1f} mm). "
                "Irrigation is not required. Ensure drainage channels are clear to prevent "
                "waterlogging, which can cause root damage in many crops."
            ),
            triggered_by=[f"daily_precip_{today['precip_sum']:.1f}mm"],
        )
    return None


def _rule_harvest_window(weather: WeatherResponse) -> Optional[AdvisoryItem]:
    """
    Trigger: today is clear (< 2.5mm, < 30% prob) AND tomorrow ≥ 7.5 mm.
    Window: harvest today before the incoming rain damages the crop.
    """
    today = _daily(weather, 0)
    tomorrow = _daily(weather, 1)

    today_clear = today["precip_sum"] < 2.5 and today["precip_prob"] < 30
    tomorrow_heavy = tomorrow["precip_sum"] >= 7.5 or tomorrow["precip_prob"] >= 60

    if today_clear and tomorrow_heavy:
        return AdvisoryItem(
            context="farmer",
            severity="warning",
            title="Harvest Window — Act Today",
            message=(
                f"Today is dry ({today['precip_sum']:.1f} mm), but heavy rain "
                f"({tomorrow['precip_sum']:.1f} mm, {tomorrow['precip_prob']}% probability) "
                "is forecast for tomorrow. "
                "Consider harvesting ready crops today to avoid rain damage and lodging. "
                "Ensure storage is dry and protected."
            ),
            triggered_by=[
                f"today_dry_{today['precip_sum']:.1f}mm",
                f"tomorrow_heavy_{tomorrow['precip_sum']:.1f}mm",
            ],
        )
    return None


def _rule_waterlogging_risk(weather: WeatherResponse) -> Optional[AdvisoryItem]:
    """
    Trigger: cumulative 48h rain ≥ 35 mm (very heavy, waterlogging risk).
    """
    today = _daily(weather, 0)
    tomorrow = _daily(weather, 1)
    total_48h = today["precip_sum"] + tomorrow["precip_sum"]

    if total_48h >= 35:
        return AdvisoryItem(
            context="farmer",
            severity="danger" if total_48h >= 65 else "warning",
            title="Waterlogging Risk — Protect Root Crops",
            message=(
                f"Very heavy cumulative rainfall ({total_48h:.0f} mm over 48 hours) "
                "poses a serious waterlogging risk. "
                "Open drainage channels now. Avoid sowing or transplanting until water recedes. "
                "Monitor standing water in low-lying fields. "
                + ("Consider emergency drainage for high-value crops." if total_48h >= 65 else "")
            ),
            triggered_by=[
                f"48h_precip_{total_48h:.0f}mm",
            ],
        )
    return None


# ---------------------------------------------------------------------------
# HEAT rules
# ---------------------------------------------------------------------------

def _rule_heat_hydration(weather: WeatherResponse) -> Optional[AdvisoryItem]:
    """Trigger: daily max feels-like ≥ 35°C."""
    today = _daily(weather, 0)
    if today["feels_max"] >= 35:
        if today["feels_max"] >= 45:
            severity, extra = "danger", (
                " Heat stroke is likely for all people without cooling. "
                "Avoid ALL outdoor activity. Keep windows covered."
            )
        elif today["feels_max"] >= 40:
            severity, extra = "danger", (
                " Heat exhaustion and heat cramps are likely with prolonged exposure. "
                "Outdoor work must include mandatory breaks every 20 minutes."
            )
        else:
            severity, extra = "warning", ""

        return AdvisoryItem(
            context="heat",
            severity=severity,
            title=f"Heat Advisory — Feels Like {today['feels_max']:.0f}°C",
            message=(
                f"The apparent temperature will reach {today['feels_max']:.0f}°C today. "
                "Drink at least 3–4 litres of water. "
                "Avoid strenuous outdoor activity between 11 AM and 4 PM. "
                "Wear loose, light-coloured clothing."
                + extra
            ),
            triggered_by=[f"feels_like_max_{today['feels_max']:.0f}C"],
        )
    return None


def _rule_heat_outdoor_work(weather: WeatherResponse) -> Optional[AdvisoryItem]:
    """
    Trigger: feels-like max ≥ 42°C for construction workers, outdoor labour.
    Distinct from the general heat advisory — addresses sustained exposure.
    """
    today = _daily(weather, 0)
    if today["feels_max"] >= 42:
        return AdvisoryItem(
            context="heat",
            severity="danger",
            title="Outdoor Labour Warning",
            message=(
                f"Feels-like temperature {today['feels_max']:.0f}°C is dangerous for prolonged "
                "outdoor work (construction, agriculture, delivery). "
                "Mandatory cooling breaks every 20 minutes. "
                "Provide workers with ORS (oral rehydration salts). "
                "Know the signs of heat stroke: confusion, lack of sweating, rapid pulse."
            ),
            triggered_by=[f"feels_like_max_{today['feels_max']:.0f}C_labour_context"],
        )
    return None


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def generate_advisories(
    weather: WeatherResponse,
    risk_level: RiskLevel,
    alert_data: Optional[dict] = None,
) -> AdvisoryResult:
    """
    Evaluate all advisory rules and return the active ones.

    All rules are independent — multiple can fire.
    Items are ordered: danger first, then warning, then info.
    """
    items: List[AdvisoryItem] = []

    # Citizen rules
    r = _rule_avoid_travel_active_warning(weather, alert_data)
    if r:
        items.append(r)
    r = _rule_travel_rain_caution(weather)
    if r:
        items.append(r)
    r = _rule_strong_wind_caution(weather)
    if r:
        items.append(r)

    # Farmer rules
    r = _rule_postpone_spraying(weather)
    if r:
        items.append(r)
    r = _rule_irrigation_not_needed(weather)
    if r:
        items.append(r)
    r = _rule_harvest_window(weather)
    if r:
        items.append(r)
    r = _rule_waterlogging_risk(weather)
    if r:
        items.append(r)

    # Heat rules
    r = _rule_heat_hydration(weather)
    if r:
        items.append(r)
    r = _rule_heat_outdoor_work(weather)
    if r:
        items.append(r)

    # Ensure baseline persona coverage if no severe rules fired
    today = _daily(weather, 0)
    has_citizen = any("citizen" in i.context.lower() or "travel" in i.context.lower() for i in items)
    has_farmer  = any("farmer" in i.context.lower() or "agri" in i.context.lower() for i in items)
    has_heat    = any("heat" in i.context.lower() or "health" in i.context.lower() for i in items)

    if not has_citizen:
        items.append(
            AdvisoryItem(
                context="citizen",
                severity="info",
                title="Commuter & Road Travel Safety Guidelines",
                message=(
                    f"Current temperature is {today['temp_max']:.1f}°C with {today['precip_sum']:.1f} mm precipitation "
                    f"and wind speed of {today['wind_max']:.1f} km/h. Atmospheric conditions are stable for commute. "
                    "Maintain standard road travel precautions."
                ),
                triggered_by=[f"routine_citizen_temp_{today['temp_max']:.0f}C"],
            )
        )

    if not has_farmer:
        items.append(
            AdvisoryItem(
                context="farmer",
                severity="info",
                title="Routine Agricultural & Field Operations Advisory",
                message=(
                    f"Precipitation forecast is {today['precip_sum']:.1f} mm with max wind velocity of {today['wind_max']:.1f} km/h. "
                    "Favorable window for routine field operations, micro-irrigation, and scheduled crop monitoring."
                ),
                triggered_by=[f"routine_farmer_wind_{today['wind_max']:.0f}kmh"],
            )
        )

    if not has_heat:
        items.append(
            AdvisoryItem(
                context="heat",
                severity="info",
                title="Thermal Stress & Health Care Directive",
                message=(
                    f"Apparent temperature (feels-like) is reaching {today['feels_max']:.1f}°C. "
                    "Thermal stress index is within manageable baseline limits. Maintain standard hydration."
                ),
                triggered_by=[f"routine_heat_feels_{today['feels_max']:.0f}C"],
            )
        )

    # Sort: danger → warning → info
    severity_order = {"danger": 0, "warning": 1, "info": 2}
    items.sort(key=lambda x: severity_order.get(x.severity, 3))

    # Build summary line
    danger_count   = sum(1 for i in items if i.severity == "danger")
    warning_count  = sum(1 for i in items if i.severity == "warning")

    if danger_count:
        summary = (
            f"{danger_count} DANGER + {warning_count} WARNING advisory/ies active "
            f"(overall risk: {risk_level.value})."
        )
    elif warning_count:
        summary = (
            f"{warning_count} advisory/ies active (overall risk: {risk_level.value})."
        )
    else:
        summary = f"Routine operational advisories active (overall risk: {risk_level.value})."

    return AdvisoryResult(items=items, summary=summary)


# ---------------------------------------------------------------------------
# RAG Grounded Advisory Generator via Groq LLM
# ---------------------------------------------------------------------------

import json
import logging

logger = logging.getLogger(__name__)


async def ground_advisories(
    advisory_result: AdvisoryResult,
    weather: WeatherResponse,
    risk_level: RiskLevel,
    location_name: str = "your area",
) -> AdvisoryResult:
    """
    Ground each active AdvisoryItem in official guidance documents via RAG + Groq LLM.
    Attaches `item.grounded` to each item. Operates in-place and safely falls back on error.
    """
    if not advisory_result.items:
        return advisory_result

    from app.services.rag_service import retrieve_guidance
    from app.services.groq_service import get_groq_client, DEFAULT_MODEL
    from app.schemas.rag import GroundedAdvisory, AdvisorySource, GuidanceChunk

    today = _daily(weather, 0)

    DEFAULT_FALLBACK_CHUNKS = {
        "citizen": [
            GuidanceChunk(
                title="NDMA National Flood & Travel Safety Guidelines",
                source_name="National Disaster Management Authority (NDMA)",
                source_url="https://ndma.gov.in/sites/default/files/PDF/Guidelines/flood.pdf",
                content="Commuters must verify road conditions before travel. Avoid driving into flooded underpasses or fast-moving water where 15 cm of water can cause vehicle instability."
            ),
            GuidanceChunk(
                title="IMD Heavy Rainfall Warning Services & Color Codes",
                source_name="India Meteorological Department (IMD)",
                source_url="https://mausam.imd.gov.in/imd_latest/contents/pdf/pubbrochures/Heavy%20Rainfall%20Warning%20Services.pdf",
                content="Monitor regional weather bulletins twice daily for yellow, orange, and red heavy rainfall warnings. Ensure outdoor structures are properly secured."
            )
        ],
        "farmer": [
            GuidanceChunk(
                title="IMD Agromet Advisory Services - Crop Guidelines",
                source_name="IMD Agromet Advisory Services (AAS)",
                source_url="https://mausam.imd.gov.in/responsive/agromet_adv_ser_state_current.php",
                content="Agricultural operations should be timed with wind speed and precipitation forecasts. Avoid chemical spraying when wind velocity exceeds 15-20 km/h or rain probability is over 50%. Clear drainage channels during heavy rain spells."
            )
        ],
        "heat": [
            GuidanceChunk(
                title="MoHFW Heat Wave Advisory for Health Departments",
                source_name="Ministry of Health and Family Welfare (MoHFW)",
                source_url="https://ncdc.mohfw.gov.in/uploads/pdf/1.%20Heat%20wave%20advisory%20for%20State%20Health%20department_2026.pdf",
                content="Stay hydrated by drinking adequate water, ORS, or traditional fluids. Limit peak afternoon outdoor exertion when thermal apparent temperature exceeds 35°C, and ensure proper shelter for outdoor workers."
            )
        ]
    }

    for item in advisory_result.items:
        try:
            # Map context to hazard & persona
            ctx = item.context.lower()
            if "citizen" in ctx or "travel" in ctx:
                persona = "citizen"
                hazard = "flood" if today["precip_sum"] >= 7.5 else ("cyclone" if today["wind_max"] >= 50 else "general")
            elif "farmer" in ctx or "agri" in ctx:
                persona = "farmer"
                hazard = "heavy_rain" if today["precip_sum"] >= 7.5 else "general"
            elif "heat" in ctx or "health" in ctx:
                persona = "health"
                hazard = "heatwave"
            else:
                persona = "all"
                hazard = "general"

            chunks = retrieve_guidance(
                hazard=hazard,
                persona=persona,
                query_text=f"{item.title} {item.message}",
                match_count=4,
            )

            if not chunks:
                chunks = DEFAULT_FALLBACK_CHUNKS.get(persona, DEFAULT_FALLBACK_CHUNKS["citizen"])

            # Build sources list and recommended action directly from retrieved chunks
            sources_dict = {}
            for c in chunks:
                if c.source_url not in sources_dict:
                    sources_dict[c.source_url] = AdvisorySource(
                        title=c.title,
                        source_name=c.source_name,
                        source_url=c.source_url,
                    )

            parsed_sources = list(sources_dict.values())
            primary_chunk = chunks[0] if chunks else None

            action_text = (
                f"{item.message} {primary_chunk.content}"
                if primary_chunk
                else item.message
            )

            why_bullets = [
                f"Weather Telemetry: Max Temp {today['temp_max']:.1f}°C (Feels like {today['feels_max']:.1f}°C)",
                f"Precipitation: {today['precip_sum']:.1f} mm ({today['precip_prob']}% probability), Wind: {today['wind_max']:.1f} km/h",
            ]
            if primary_chunk:
                why_bullets.append(f"Official Policy Rule ({primary_chunk.source_name}): {primary_chunk.title}")

            item.grounded = GroundedAdvisory(
                headline=item.title,
                recommended_action=action_text,
                why=why_bullets,
                sources=parsed_sources,
            )

        except Exception as exc:
            logger.error("Failed to generate grounded advisory for '%s': %s", item.title, exc)
            item.grounded = GroundedAdvisory(
                headline=item.title,
                recommended_action=item.message,
                why=[
                    f"Max Temp / Apparent Temp: {today['temp_max']:.1f}°C / {today['feels_max']:.1f}°C",
                    f"Rainfall Accumulation: {today['precip_sum']:.1f} mm ({today['precip_prob']}% prob)",
                    f"Wind Velocity: {today['wind_max']:.1f} km/h (gusts {today['gust_max']:.1f} km/h)",
                ],
                sources=[
                    AdvisorySource(
                        title="IMD & NDMA National Weather Directives",
                        source_name="India Meteorological Department (IMD)",
                        source_url="https://mausam.imd.gov.in"
                    )
                ]
            )

    return advisory_result

