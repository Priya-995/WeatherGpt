"""
Weather service — fetches forecast data from Open-Meteo (no API key required).

Open-Meteo docs: https://open-meteo.com/en/docs

Features
--------
- Fetches current conditions, hourly (48 h) and daily (7-day) forecasts.
- Simple in-memory LRU-style cache keyed on (lat, lon) rounded to 2 dp.
  Cache TTL: CACHE_TTL_SECONDS (default 10 minutes).
- Raises WeatherServiceError on upstream failure so callers can return a
  clean HTTP error rather than letting the exception propagate.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

import httpx

from app.schemas.weather import (
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    WeatherResponse,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS = 600  # 10 minutes
REQUEST_TIMEOUT = 10.0  # seconds

# Fields we request from the API
_CURRENT_VARS = ",".join([
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
])

_HOURLY_VARS = ",".join([
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "precipitation_probability",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "wind_gusts_10m",
])

_DAILY_VARS = ",".join([
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "weather_code",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "sunrise",
    "sunset",
])


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class WeatherServiceError(Exception):
    """Raised when the Open-Meteo API call fails or returns unexpected data."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

@dataclass
class _CacheEntry:
    response: WeatherResponse
    fetched_at: float = field(default_factory=time.monotonic)


# Module-level cache dict:  (lat_rounded, lon_rounded) -> _CacheEntry
_cache: Dict[Tuple[float, float], _CacheEntry] = {}


def _cache_key(lat: float, lon: float) -> Tuple[float, float]:
    """Round coordinates to 2 decimal places (~1 km precision) for cache keying."""
    return (round(lat, 2), round(lon, 2))


def _get_cached(lat: float, lon: float) -> WeatherResponse | None:
    key = _cache_key(lat, lon)
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry.fetched_at) < CACHE_TTL_SECONDS:
        return entry.response
    # Evict stale entry if present
    if entry:
        del _cache[key]
    return None


def _set_cache(lat: float, lon: float, response: WeatherResponse) -> None:
    _cache[_cache_key(lat, lon)] = _CacheEntry(response=response)


# ---------------------------------------------------------------------------
# Core fetch function
# ---------------------------------------------------------------------------

def _parse_response(data: Dict[str, Any], cached: bool = False) -> WeatherResponse:
    """
    Map the raw Open-Meteo JSON dict into a validated WeatherResponse.
    Raises WeatherServiceError if expected keys are missing.
    """
    try:
        current_raw = data["current"]
        hourly_raw = data["hourly"]
        daily_raw = data["daily"]

        current = CurrentWeather(
            time=current_raw["time"],
            temperature_2m=current_raw["temperature_2m"],
            relative_humidity_2m=current_raw["relative_humidity_2m"],
            apparent_temperature=current_raw["apparent_temperature"],
            precipitation=current_raw["precipitation"],
            weather_code=current_raw["weather_code"],
            cloud_cover=current_raw["cloud_cover"],
            wind_speed_10m=current_raw["wind_speed_10m"],
            wind_gusts_10m=current_raw["wind_gusts_10m"],
            wind_direction_10m=current_raw["wind_direction_10m"],
        )

        hourly = HourlyForecast(
            time=hourly_raw["time"],
            temperature_2m=hourly_raw["temperature_2m"],
            relative_humidity_2m=hourly_raw["relative_humidity_2m"],
            apparent_temperature=hourly_raw["apparent_temperature"],
            precipitation=hourly_raw["precipitation"],
            precipitation_probability=hourly_raw["precipitation_probability"],
            weather_code=hourly_raw["weather_code"],
            cloud_cover=hourly_raw["cloud_cover"],
            wind_speed_10m=hourly_raw["wind_speed_10m"],
            wind_gusts_10m=hourly_raw["wind_gusts_10m"],
        )

        daily = DailyForecast(
            time=daily_raw["time"],
            temperature_2m_max=daily_raw["temperature_2m_max"],
            temperature_2m_min=daily_raw["temperature_2m_min"],
            apparent_temperature_max=daily_raw["apparent_temperature_max"],
            apparent_temperature_min=daily_raw["apparent_temperature_min"],
            precipitation_sum=daily_raw["precipitation_sum"],
            precipitation_probability_max=daily_raw["precipitation_probability_max"],
            weather_code=daily_raw["weather_code"],
            wind_speed_10m_max=daily_raw["wind_speed_10m_max"],
            wind_gusts_10m_max=daily_raw["wind_gusts_10m_max"],
            sunrise=daily_raw["sunrise"],
            sunset=daily_raw["sunset"],
        )

        return WeatherResponse(
            latitude=data["latitude"],
            longitude=data["longitude"],
            timezone=data.get("timezone", "UTC"),
            elevation=data.get("elevation", 0.0),
            current=current,
            hourly=hourly,
            daily=daily,
            cached=cached,
        )

    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherServiceError(
            f"Unexpected Open-Meteo response structure: {exc}", status_code=502
        ) from exc


async def get_forecast(lat: float, lon: float) -> WeatherResponse:
    """
    Return a validated WeatherResponse for the given coordinates.

    Results are cached in-memory for CACHE_TTL_SECONDS (10 minutes).
    Raises WeatherServiceError on network failure, timeout, or bad data.
    """
    # --- Cache hit ---
    cached_response = _get_cached(lat, lon)
    if cached_response is not None:
        # Return a copy with cached=True so callers can detect it
        return cached_response.model_copy(update={"cached": True})

    # --- Fetch from Open-Meteo ---
    params: Dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "current": _CURRENT_VARS,
        "hourly": _HOURLY_VARS,
        "daily": _DAILY_VARS,
        "forecast_days": 7,
        "timezone": "auto",  # let Open-Meteo resolve the local timezone
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()

    except httpx.TimeoutException as exc:
        raise WeatherServiceError(
            "Open-Meteo request timed out. Please try again later.", status_code=504
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise WeatherServiceError(
            f"Open-Meteo returned HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            status_code=502,
        ) from exc
    except httpx.RequestError as exc:
        raise WeatherServiceError(
            f"Network error contacting Open-Meteo: {exc}", status_code=503
        ) from exc

    weather = _parse_response(data, cached=False)
    _set_cache(lat, lon, weather)
    return weather
