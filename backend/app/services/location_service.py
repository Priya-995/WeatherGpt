"""
Location service — resolves place names to coordinates via Open-Meteo's
free geocoding API (no API key required).

Open-Meteo Geocoding docs: https://open-meteo.com/en/docs/geocoding-api

Design notes
------------
- Returns ALL matches; the caller decides how to present ambiguous results
  (e.g. multiple "Springfield" entries).  We never silently pick one.
- Empty results are not an error — the route returns an empty list with
  count=0 so the frontend can show a friendly "no results" state.
- Network / upstream failures raise GeocodingServiceError so the router
  can surface a clean HTTP error.
- Results are cached in-memory for CACHE_TTL_SECONDS (5 minutes) per
  (query, count) pair to avoid hammering the geocoding API.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import httpx

from app.schemas.location import Location

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
CACHE_TTL_SECONDS = 300   # 5 minutes — geocoding results change rarely
MAX_RESULTS = 10          # cap returned by default
REQUEST_TIMEOUT = 10.0    # seconds


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class GeocodingServiceError(Exception):
    """Raised when the geocoding API call fails."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

@dataclass
class _CacheEntry:
    results: List[Location]
    fetched_at: float = field(default_factory=time.monotonic)


# (normalised_query, count) -> _CacheEntry
_cache: Dict[Tuple[str, int], _CacheEntry] = {}


def _cache_key(query: str, count: int) -> Tuple[str, int]:
    return (query.strip().lower(), count)


def _get_cached(query: str, count: int) -> List[Location] | None:
    key = _cache_key(query, count)
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry.fetched_at) < CACHE_TTL_SECONDS:
        return entry.results
    if entry:
        del _cache[key]
    return None


def _set_cache(query: str, count: int, results: List[Location]) -> None:
    _cache[_cache_key(query, count)] = _CacheEntry(results=results)


# ---------------------------------------------------------------------------
# Core fetch + parse
# ---------------------------------------------------------------------------

def _parse_location(raw: dict) -> Location:
    """Map a single Open-Meteo geocoding result dict to a Location model."""
    return Location(
        id=raw["id"],
        name=raw["name"],
        latitude=raw["latitude"],
        longitude=raw["longitude"],
        country=raw.get("country", ""),
        country_code=raw.get("country_code", ""),
        admin1=raw.get("admin1"),
        admin2=raw.get("admin2"),
        admin3=raw.get("admin3"),
        timezone=raw.get("timezone"),
        elevation=raw.get("elevation"),
        population=raw.get("population"),
        feature_code=raw.get("feature_code"),
    )


async def geocode(place_name: str, count: int = MAX_RESULTS) -> List[Location]:
    """
    Resolve a place name to a list of matching Location objects.

    - Returns an empty list (not an error) if no matches are found.
    - Returns ALL matches up to *count* — callers must handle ambiguity.
    - Results are cached in-memory for 5 minutes.
    - Raises GeocodingServiceError on network failure or unexpected response.
    """
    # --- Cache hit ---
    cached = _get_cached(place_name, count)
    if cached is not None:
        return cached

    # --- Fetch from Open-Meteo Geocoding API ---
    params = {
        "name": place_name.strip(),
        "count": count,
        "language": "en",
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(GEOCODING_URL, params=params)
            resp.raise_for_status()
            data: dict = resp.json()

    except httpx.TimeoutException as exc:
        raise GeocodingServiceError(
            "Geocoding request timed out. Please try again later.", status_code=504
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise GeocodingServiceError(
            f"Geocoding API returned HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            status_code=502,
        ) from exc
    except httpx.RequestError as exc:
        raise GeocodingServiceError(
            f"Network error contacting geocoding API: {exc}", status_code=503
        ) from exc

    # Open-Meteo returns {"results": [...]} or {} (no key) when empty
    raw_results: list = data.get("results", [])

    try:
        locations = [_parse_location(r) for r in raw_results]
    except (KeyError, TypeError, ValueError) as exc:
        raise GeocodingServiceError(
            f"Unexpected geocoding response structure: {exc}", status_code=502
        ) from exc

    _set_cache(place_name, count, locations)
    return locations
