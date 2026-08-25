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
import re
from functools import lru_cache
from typing import Any, Dict, List

from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Language detection dictionaries & helpers
# ---------------------------------------------------------------------------

LANGUAGE_NAMES: Dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "hi-en": "Hinglish (Hindi in Latin script)",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "or": "Odia",
    "ur": "Urdu",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
}

# Common Romanized Hindi/Hinglish vocabulary tokens
HINGLISH_KEYWORDS = {
    "kya", "kyu", "kyun", "kaise", "kaisa", "kaisi", "kab", "kahan", "kaha", "kidhar",
    "kon", "kaun", "kitna", "kitni", "kitne", "kal", "aaj", "parso", "subah", "shaam",
    "raat", "dopahar", "din", "mausam", "barish", "barsaat", "baarish", "paani", "pani",
    "hawa", "badal", "dhoop", "garmi", "thand", "sardi", "toofan", "aandhi", "tapman",
    "fasal", "khet", "kheti", "kisaan", "kisano", "spray", "pesticide", "fertilizer",
    "khad", "kar", "kare", "karein", "karna", "karega", "karegi", "karenge", "sakta",
    "sakti", "sakte", "chahiye", "hoga", "hogi", "honge", "hai", "hain", "hoon", "hu",
    "tha", "thi", "the", "rahega", "rahegi", "rahenge", "batao", "bataiye", "boliye",
    "bata", "dekh", "dekho", "mera", "meri", "mere", "mujhe", "mujhko", "hum", "hume",
    "humein", "humara", "humari", "humare", "aap", "aapka", "aapki", "aapke", "tum",
    "tumhara", "tumhari", "tumhare", "accha", "theek", "bhi", "nahi", "mat", "karo",
    "pehle", "baad", "mein", "me", "par", "se", "ko", "ka", "ki", "ke", "namaste",
    "chhatri", "gari", "gaadi", "chalo", "jaana", "ja sakte", "ruk", "suno"
}


def detect_language(text: str) -> str:
    """
    Detect the likely language/script of a given text.
    Returns: 'hi', 'hi-en', 'bn', 'ta', 'te', 'mr', 'gu', 'pa', 'kn', 'ml', 'ur', or 'en'.
    """
    if not text or not text.strip():
        return "en"

    cleaned = text.strip()

    # 1. Indic Unicode Script Checks
    if re.search(r"[\u0900-\u097F]", cleaned):
        return "hi"  # Devanagari (Hindi/Marathi)
    if re.search(r"[\u0980-\u09FF]", cleaned):
        return "bn"  # Bengali / Assamese
    if re.search(r"[\u0B80-\u0BFF]", cleaned):
        return "ta"  # Tamil
    if re.search(r"[\u0C00-\u0C7F]", cleaned):
        return "te"  # Telugu
    if re.search(r"[\u0A80-\u0AFF]", cleaned):
        return "gu"  # Gujarati
    if re.search(r"[\u0A00-\u0A7F]", cleaned):
        return "pa"  # Punjabi
    if re.search(r"[\u0C80-\u0CFF]", cleaned):
        return "kn"  # Kannada
    if re.search(r"[\u0D00-\u0D7F]", cleaned):
        return "ml"  # Malayalam
    if re.search(r"[\u0B00-\u0B7F]", cleaned):
        return "or"  # Odia
    if re.search(r"[\u0600-\u06FF]", cleaned):
        return "ur"  # Urdu / Arabic

    # 2. Hinglish (Latin-script Hindi) Detection
    words = re.findall(r"\b[a-zA-Z]+\b", cleaned.lower())
    if words:
        matches = [w for w in words if w in HINGLISH_KEYWORDS]
        # If at least 1 strong indicator word or multiple words match
        if len(matches) >= 1:
            return "hi-en"

    return "en"


# ---------------------------------------------------------------------------
# Default model — fast, capable, supports parallel tool calls
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "qwen/qwen3.6-27b"


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
    {
        "type": "function",
        "function": {
            "name": "get_risk",
            "description": (
                "Compute a deterministic risk score and rule-based advisories for "
                "a location. Call this when the user asks about safety, risk level, "
                "travel advisories, farming recommendations (spraying, irrigation, "
                "harvest), or heat/health precautions. "
                "Returns: composite risk score (0–1), risk level (Low/Moderate/High/Critical), "
                "plain-English reasons, and active advisory messages for citizen, "
                "farmer, and heat contexts. "
                "Always call search_location + get_weather first, then call this."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {
                        "type": "number",
                        "description": "Latitude in decimal degrees",
                    },
                    "lon": {
                        "type": "number",
                        "description": "Longitude in decimal degrees",
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
6. When the user asks about risk, safety, travel advisories, farming actions
   (spraying, irrigation, harvest), or heat precautions — call get_risk after
   get_weather to get the deterministic risk score and rule-based advisory text.
   Quote the advisory message directly; it is already human-readable.

INTENT CATEGORIES you handle:
  - current_weather   : real-time conditions at a location
  - forecast          : upcoming hours or days outlook
  - rain_query        : precipitation probability and amounts
  - travel_advisory   : safety/travel guidance — use get_risk
  - farmer_advisory   : spraying/irrigation/harvest guidance — use get_risk
  - heat_advisory     : hydration/heat precautions — use get_risk

ANSWER STYLE:
- Be concise, friendly, and specific. Quote exact figures from the tool data.
- Mention the data source (Open-Meteo) when relevant for credibility.
- Use local time (the API returns local timestamps automatically).
- For rain queries, always state the precipitation probability percentage AND
  the expected amount in mm, not just a vague "yes/no".
- For advisory queries, quote the advisory title and message from get_risk results.
"""


def get_system_prompt(language: str = "auto") -> str:
    """
    Return the system prompt with language-specific instructions appended.
    Supported languages:
      - 'auto': Automatically detect the user's language/script and respond in the same language.
      - 'hi': Hindi (Devanagari script).
      - 'hi-en': Hinglish (Hindi written in Latin/English script).
      - 'en': English.
      - Other standard language codes (e.g. 'bn', 'ta', 'te', 'mr', 'gu', 'pa', 'ur', 'es', 'fr').
    """
    lang_code = (language or "auto").lower().strip()

    if lang_code in ("auto", "detect", "auto-detect", "default"):
        lang_instruction = (
            "\n\nCRITICAL LANGUAGE & SCRIPT INSTRUCTION (AUTO-DETECT & MATCH USER LANGUAGE):\n"
            "1. AUTOMATICALLY DETECT the language, script, and phrasing style used by the user in their question.\n"
            "2. ALWAYS generate your entire response in the EXACT SAME language, script, and style as the user's message:\n"
            "   - If the user asks in Hindi using Devanagari script (e.g. 'क्या कल बारिश होगी?'), you MUST respond entirely in Hindi using Devanagari script.\n"
            "   - If the user asks in Hinglish / Latin-script Hindi (e.g. 'kal barish hogi kya?', 'Delhi me mausam kaisa rahega?'), you MUST respond in natural, conversational Hinglish (Hindi written in Latin/English script).\n"
            "   - If the user asks in any regional Indian language (Bengali, Tamil, Telugu, Marathi, Gujarati, Punjabi, Kannada, Malayalam, Odia, Urdu, etc.), you MUST respond in that regional language and its authentic script.\n"
            "   - If the user asks in English, respond in clear, natural English.\n"
            "   - If the user asks in Spanish, French, German, or any other language, respond in that language.\n"
            "3. NEVER revert or default to English if the user asked their question in Hindi, Hinglish, or any non-English language.\n"
            "4. Numeric Accuracy: Keep all numeric values, temperatures (°C), precipitation (mm), wind speeds (km/h), percentages (%), dates, times, and place names exact and unchanged from the tool data."
        )
    elif lang_code in ("hi", "hindi"):
        lang_instruction = (
            "\n\nLANGUAGE INSTRUCTION: Respond entirely in Hindi using Devanagari script. "
            "Explain clearly in Hindi, but keep all numeric values, temperatures (°C), precipitation (mm), "
            "wind speeds (km/h), percentages (%), dates, and place names exact and unchanged from the tool data."
        )
    elif lang_code in ("hi-en", "hinglish"):
        lang_instruction = (
            "\n\nLANGUAGE INSTRUCTION: Respond in natural, conversational Hinglish (Hindi written in Latin/English script). "
            "For example: 'Aap kal pesticide spray nahi kar sakte kyunki 80% rain probability hai (2.5 mm rainfall expected).' "
            "Keep all numeric values, temperatures, wind speeds, percentages, and units exact and unchanged from the tool data."
        )
    elif lang_code in ("en", "english"):
        lang_instruction = "\n\nLANGUAGE INSTRUCTION: Respond in clear, natural English."
    else:
        lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)
        lang_instruction = (
            f"\n\nLANGUAGE INSTRUCTION: Respond entirely in {lang_name}. "
            "Keep all numeric values, temperatures (°C), precipitation (mm), wind speeds (km/h), "
            "percentages (%), dates, and place names exact and unchanged from the tool data."
        )

    return SYSTEM_PROMPT + lang_instruction

