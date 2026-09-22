"""
Risk & Advisory API router — GET /api/risk?lat=..&lon=..

Composes weather data → risk scoring → advisory generation into a single
transparent response that shows both the final verdict AND the reasoning.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.schemas.risk import RiskLevel, RiskResult
from app.services.rag_advisory_engine import generate_advisories, ground_advisories
from app.services.alert_service import get_alert_data_for_risk_engine
from app.services.risk_engine import calculate_risk
from app.services.weather_service import WeatherServiceError, get_forecast

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get(
    "",
    response_model=RiskResult,
    summary="Get risk score and advisories for a location",
    description=(
        "Fetches real weather data for the given coordinates, runs the deterministic "
        "risk scoring formula (rainfall × 0.30 + wind × 0.20 + temperature × 0.15 + "
        "official warning × 0.35), and generates rule-based advisories for citizen, "
        "farmer, and heat contexts. Every score and recommendation is fully transparent "
        "— the sub-score breakdown and triggered rules are included in the response."
    ),
)
async def get_risk(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude (decimal degrees)"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude (decimal degrees)"),
    persona: Optional[str] = Query(None, description="Optional persona filter (citizen, farmer, heat)"),
) -> RiskResult:
    """
    Returns a `RiskResult` containing:
    - **score** — composite 0–1 risk score
    - **level** — Low / Moderate / High / Critical
    - **reasons** — plain-English explanation of the score drivers
    - **sub_scores** — per-component breakdown (rainfall, wind, temperature, official warning)
    - **advisory.items** — active rule-based recommendations (grounded with RAG sources)
    - **advisory.summary** — one-line overall advisory summary
    """
    try:
        weather = await get_forecast(lat, lon)
    except WeatherServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    # Fetch active alerts affecting this location from the store
    alert_data = get_alert_data_for_risk_engine(lat, lon)

    # Pass 1: score (with real alert data) to get the risk level
    preliminary = calculate_risk(weather, alert_data=alert_data)

    # Pass 2: generate advisory using RAG engine for the selected persona
    advisory = generate_advisories(weather, risk_result=preliminary, alert_data=alert_data, persona=persona or "citizen")

    # Filter items by persona if requested
    if persona:
        p_lower = persona.lower().strip()
        filtered_items = [
            item for item in advisory.items
            if p_lower in item.context.lower() or "all" in item.context.lower()
        ]
        if filtered_items:
            advisory.items = filtered_items

    # RAG Grounding via Groq + Supabase pgvector
    advisory = await ground_advisories(
        advisory_result=advisory,
        weather=weather,
        risk_level=preliminary.level,
        location_name=f"lat {lat:.2f}, lon {lon:.2f}",
    )

    result = calculate_risk(weather, alert_data=alert_data, advisory=advisory)

    # Push through WebSocket alert channel for High/Critical risk
    if result.level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        try:
            from app.api.routes.websocket import broadcast_alert
            for item in result.advisory.items:
                headline = item.grounded.headline if item.grounded else item.title
                await broadcast_alert({
                    "type": "risk_escalation",
                    "severity": result.level.value.lower(),
                    "location": f"{lat:.2f}, {lon:.2f}",
                    "headline": headline,
                    "score": result.score,
                })
        except Exception:
            pass  # Non-blocking WS notification

    return result

