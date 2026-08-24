"""
Groq LLM client setup and tool schema definitions.

This module owns:
  - The Groq async client (lazy-initialised, fails fast if key is missing).
  - The JSON Schema tool definitions that map our backend functions to
    Groq's function-calling format.
  - The system prompt that constrains the LLM to ONLY use real tool data.

Tools exposed to the LLM
-------------------------
  get_weather(lat, lon)       → calls weather_service.get_forecast()
  search_location(query)      → calls location_service.geocode()

The LLM is NEVER allowed to invent weather numbers. The system prompt
enforces this, and the orchestrator validates it by only injecting data
that comes from actual tool results.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List

from groq import AsyncGroq

# ---------------------------------------------------------------------------
# Default model — fast, capable, supports parallel tool calls
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024


# ---------------------------------------------------------------------------
# Client factory  (constructed once per process)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_groq_client() -> AsyncGroq:
    """
    Return a cached AsyncGroq client.
    Raises RuntimeError immediately if GROQ_API_KEY is not set so the
    developer gets a clear error at startup / first request rather than
    a cryptic downstream failure.
    """
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set. "
            "Copy backend/.env.example to backend/.env and fill in your key."
        )
    return AsyncGroq(api_key=api_key)


# ---------------------------------------------------------------------------
# Tool definitions  (JSON Schema, Groq function-calling format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_location",
            "description": (
                "Resolve a place name (city, neighbourhood, landmark) to geographic "
                "coordinates. Always call this first when the user mentions a place "
                "by name, unless coordinates are already known. "
                "Returns a list of matching locations with name, latitude, longitude, "
                "country, and administrative area. If multiple results are returned, "
                "prefer the first result unless context clearly indicates otherwise."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The place name to search for. "
                            "Be specific (e.g. 'Noida, India') to reduce ambiguity."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Fetch real current weather conditions plus 48-hour hourly and "
                "7-day daily forecasts for a specific latitude/longitude pair. "
                "You MUST have called search_location first to obtain coordinates "
                "unless the user already provided lat/lon directly. "
                "Data comes from Open-Meteo's GFS model — use ONLY these numbers "
                "in your answer. Never invent or estimate weather values."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {
                        "type": "number",
                        "description": "Latitude in decimal degrees (e.g. 28.58)",
                    },
                    "lon": {
                        "type": "number",
                        "description": "Longitude in decimal degrees (e.g. 77.33)",
                    },
                },
                "required": ["lat", "lon"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are WeatherGPT, an AI-powered weather intelligence assistant.

CRITICAL RULES — you must follow these without exception:
1. You MUST call the provided tools to get real weather data before answering.
2. You MUST NEVER invent, estimate, or hallucinate weather numbers (temperature,
   precipitation, wind speed, humidity, etc.). Every number you state must come
   directly from a tool result.
3. Always call search_location first when a place name is mentioned, then call
   get_weather with the returned coordinates.
4. If a location cannot be found, say so clearly and ask the user to clarify.
5. If the weather data does not cover the requested time window, say so honestly.

INTENT CATEGORIES you handle:
  - current_weather   : real-time conditions at a location
  - forecast          : upcoming hours or days outlook
  - rain_query        : precipitation probability and amounts
  - travel_advisory   : whether conditions are suitable for travel/outdoor activity
  - farmer_advisory   : crop/irrigation guidance based on precipitation & temperature

ANSWER STYLE:
- Be concise, friendly, and specific. Quote exact figures from the tool data.
- Mention the data source (Open-Meteo) when relevant for credibility.
- Use local time (the API returns local timestamps automatically).
- For rain queries, always state the precipitation probability percentage AND
  the expected amount in mm, not just a vague "yes/no".
"""
