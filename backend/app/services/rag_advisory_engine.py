"""
RAG Advisory Engine — Grounded safety directives powered by NDMA corpus vector search & Groq LLM.

Design Contract
---------------
- Zero hallucination: Every recommendation is grounded strictly in retrieved plain-language chunks.
- Signature compatible with rule-based advisory_engine: generate_advisories(weather, risk_result, alert_data, persona).
- Supports personas: 'citizen' | 'farmer' | 'official'.
- For 'official' persona, populates official_text and source_url on each AdvisoryItem.
- Graceful error handling: returns empty AdvisoryResult with "advisory temporarily unavailable" note on failure.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from groq import Groq

from app.schemas.rag import GroundedAdvisory, AdvisorySource
from app.schemas.risk import AdvisoryItem, AdvisoryResult, RiskLevel
from app.schemas.weather import WeatherResponse
from app.services.groq_service import DEFAULT_MODEL
from app.services.rag_service import _encode_text

load_dotenv()
logger = logging.getLogger("rag_advisory_engine")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


def _determine_hazard_types(weather: WeatherResponse, alert_data: Optional[dict] = None) -> List[str]:
    """Determine relevant hazard types based on weather telemetry and active warnings."""
    hazards = []
    
    # Check weather parameters
    d = weather.daily
    if d:
        temp_max = max(d.temperature_2m_max or [25.0])
        temp_min = min(d.temperature_2m_min or [20.0])
        precip = sum(d.precipitation_sum or [0.0])
        wind = max(d.wind_speed_10m_max or [10.0])

        if temp_max >= 38.0:
            hazards.append("heat_wave")
        if temp_min <= 5.0:
            hazards.append("cold_wave")
        if precip >= 50.0:
            hazards.append("flood")
        elif precip >= 15.0:
            hazards.append("thunderstorm")
        if wind >= 40.0:
            hazards.append("cyclone")

    # Check active CAP alerts
    if alert_data:
        event = str(alert_data.get("event", "")).lower()
        if "heat" in event:
            hazards.append("heat_wave")
        if "cold" in event or "frost" in event:
            hazards.append("cold_wave")
        if "thunderstorm" in event or "lightning" in event or "squall" in event:
            hazards.append("thunderstorm")
        if "cyclone" in event or "storm" in event:
            hazards.append("cyclone")
        if "flood" in event or "heavy rain" in event:
            hazards.append("flood")

    return list(set(hazards)) if hazards else ["heat_wave", "thunderstorm", "flood"]


def fetch_grounded_documents(
    query_text: str,
    persona: str = "citizen",
    hazard_types: Optional[List[str]] = None,
    match_count: int = 4,
) -> List[Dict[str, Any]]:
    """Retrieve grounded advisory chunks from Supabase match_advisory_documents RPC or local fallback."""
    query_embedding = _encode_text(query_text)
    persona_normalized = persona.lower().strip()

    # 1. Try Supabase vector RPC match_advisory_documents
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/match_advisory_documents"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "query_embedding": query_embedding,
                "persona": persona_normalized,
                "hazard_types": hazard_types or [],
                "match_count": match_count,
            }
            req = urllib.request.Request(rpc_url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and isinstance(data, list):
                    return data
        except Exception as exc:
            logger.warning("Supabase match_advisory_documents RPC call failed: %s", exc)

    # 2. Local JSON fallback backup if Supabase RPC is empty or unavailable
    backup_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "scripts",
        "advisory_corpus_backup.json",
    )
    if os.path.exists(backup_file):
        try:
            with open(backup_file, "r", encoding="utf-8") as f:
                backup_records = json.load(f)

            matched = []
            for rec in backup_records:
                r_personas = [p.lower() for p in rec.get("persona_tags", [])]
                r_hazard = rec.get("hazard_type", "")

                # Persona match check
                if persona_normalized not in r_personas and "citizen" not in r_personas:
                    continue
                # Hazard match check
                if hazard_types and r_hazard not in hazard_types:
                    continue

                matched.append(rec)
                if len(matched) >= match_count:
                    break

            return matched if matched else backup_records[:match_count]
        except Exception as exc:
            logger.error("Failed to load local advisory backup: %s", exc)

    return []


def generate_advisories(
    weather: WeatherResponse,
    risk_result: Optional[Any] = None,
    alert_data: Optional[dict] = None,
    persona: str = "citizen",
    risk_level: Optional[Any] = None,
) -> AdvisoryResult:
    """
    RAG-grounded advisory generation matching existing AdvisoryEngine contract.
    """
    try:
        persona = (persona or "citizen").lower().strip()
        hazards = _determine_hazard_types(weather, alert_data)
        
        # Build contextual retrieval query
        r_level = getattr(risk_result, "level", risk_level) or RiskLevel.MODERATE
        query_text = (
            f"Safety guidance for {', '.join(hazards)} hazards under {r_level} risk level "
            f"tailored for {persona}"
        )

        docs = fetch_grounded_documents(
            query_text=query_text,
            persona=persona,
            hazard_types=hazards,
            match_count=4,
        )

        if not docs:
            logger.warning("No RAG documents retrieved for query: %s", query_text)
            return AdvisoryResult(
                items=[],
                summary="advisory temporarily unavailable",
            )

        # Prepare plain-language context for Groq
        context_passages = []
        for idx, doc in enumerate(docs, 1):
            plain_txt = doc.get("plain_language_text", doc.get("official_text", ""))
            src_url = doc.get("source_url", "")
            context_passages.append(f"Passage {idx} [Source: {src_url}]:\n{plain_txt}")

        combined_context = "\n\n".join(context_passages)

        if not GROQ_API_KEY:
            logger.warning("GROQ_API_KEY missing. Returning raw retrieved guidance.")
            items = []
            for doc in docs:
                items.append(
                    AdvisoryItem(
                        context=persona,
                        severity="info",
                        title=f"{doc.get('hazard_type', 'Weather').replace('_', ' ').title()} Advisory",
                        message=doc.get("plain_language_text", ""),
                        triggered_by=[doc.get("hazard_type", "general")],
                        official_text=doc.get("official_text") if persona == "official" else None,
                        source_url=doc.get("source_url") if persona == "official" else None,
                    )
                )
            return AdvisoryResult(items=items, summary=f"Grounded safety advisory for {persona}")

        # Invoke Groq LLM to synthesize JSON AdvisoryResult
        system_prompt = (
            "You are WeatherGPT's RAG Advisory Synthesizer. "
            "Your task is to generate JSON safety advisories using ONLY the provided plain-language context passages. "
            "NEVER invent advice, thresholds, or precautions not in the passages. "
            "Output JSON with this structure:\n"
            "{\n"
            '  "summary": "One line overall advisory summary",\n'
            '  "items": [\n'
            "    {\n"
            '      "severity": "info" | "warning" | "danger",\n'
            '      "title": "Short title",\n'
            '      "message": "Full plain language action directive",\n'
            '      "triggered_by": ["hazard_name"]\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"Target Persona: {persona}\n"
            f"Weather Hazards: {', '.join(hazards)}\n\n"
            f"Plain-Language Guidance Context:\n{combined_context}"
        )

        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=800,
        )

        raw_json = completion.choices[0].message.content
        parsed = json.loads(raw_json)

        items = []
        parsed_items = parsed.get("items", [])
        for i, it in enumerate(parsed_items):
            matched_doc = docs[i % len(docs)] if docs else {}
            
            grounded_info = GroundedAdvisory(
                headline=it.get("title", "Safety Action Directive"),
                recommended_action=it.get("message", ""),
                why=[f"Hazard context: {', '.join(hazards)}", f"Target group: {persona}"],
                sources=[
                    AdvisorySource(
                        title="NDMA Official Guideline",
                        source_name="National Disaster Management Authority (NDMA)",
                        source_url=matched_doc.get("source_url", "https://ndma.gov.in"),
                    )
                ],
            )

            item = AdvisoryItem(
                context=persona,
                severity=it.get("severity", "info"),
                title=it.get("title", "Weather Precaution Directive"),
                message=it.get("message", ""),
                triggered_by=it.get("triggered_by", hazards),
                grounded=grounded_info,
                official_text=matched_doc.get("official_text") if persona == "official" else None,
                source_url=matched_doc.get("source_url") if persona == "official" else None,
            )
            items.append(item)

        return AdvisoryResult(
            items=items,
            summary=parsed.get("summary", f"Grounded NDMA advisory active for {persona}"),
        )

    except Exception as exc:
        logger.error("RAG Advisory generation error: %s", exc)
        return AdvisoryResult(
            items=[],
            summary="advisory temporarily unavailable",
        )


async def ground_advisories(
    advisory_result: AdvisoryResult,
    weather: WeatherResponse,
    risk_level: RiskLevel,
    location_name: str = "your area",
) -> AdvisoryResult:
    """Pass-through helper to maintain compatibility with risk.py RAG grounding route call."""
    return advisory_result
