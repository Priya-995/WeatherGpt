"""
Pydantic schemas for the weather response.

Mirrors the fields returned by Open-Meteo's /v1/forecast endpoint so that
every outbound API response is validated and documented.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Current-conditions block
# ---------------------------------------------------------------------------

class CurrentWeather(BaseModel):
    time: str = Field(..., description="ISO-8601 timestamp (local time at the queried location)")
    temperature_2m: float = Field(..., description="Air temperature at 2 m above ground (°C)")
    relative_humidity_2m: int = Field(..., description="Relative humidity at 2 m (%)")
    apparent_temperature: float = Field(..., description="Feels-like temperature (°C)")
    precipitation: float = Field(..., description="Precipitation in the last hour (mm)")
    weather_code: int = Field(..., description="WMO weather interpretation code")
    cloud_cover: int = Field(..., description="Total cloud cover (%)")
    wind_speed_10m: float = Field(..., description="Wind speed at 10 m (km/h)")
    wind_gusts_10m: float = Field(..., description="Wind gusts at 10 m (km/h)")
    wind_direction_10m: int = Field(..., description="Wind direction at 10 m (°)")


# ---------------------------------------------------------------------------
# Hourly block  (next 48 h, index-aligned lists)
# ---------------------------------------------------------------------------

class HourlyForecast(BaseModel):
    time: List[str] = Field(..., description="List of hourly ISO-8601 timestamps")
    temperature_2m: List[float] = Field(..., description="Hourly temperature at 2 m (°C)")
    relative_humidity_2m: List[int] = Field(..., description="Hourly relative humidity (%)")
    apparent_temperature: List[float] = Field(..., description="Hourly feels-like temperature (°C)")
    precipitation: List[float] = Field(..., description="Hourly precipitation (mm)")
    precipitation_probability: List[Optional[int]] = Field(
        ..., description="Hourly precipitation probability (%)"
    )
    weather_code: List[int] = Field(..., description="Hourly WMO weather code")
    cloud_cover: List[int] = Field(..., description="Hourly cloud cover (%)")
    wind_speed_10m: List[float] = Field(..., description="Hourly wind speed at 10 m (km/h)")
    wind_gusts_10m: List[float] = Field(..., description="Hourly wind gusts at 10 m (km/h)")


# ---------------------------------------------------------------------------
# Daily block  (next 7 days, index-aligned lists)
# ---------------------------------------------------------------------------

class DailyForecast(BaseModel):
    time: List[str] = Field(..., description="List of daily date strings (YYYY-MM-DD)")
    temperature_2m_max: List[float] = Field(..., description="Daily maximum temperature (°C)")
    temperature_2m_min: List[float] = Field(..., description="Daily minimum temperature (°C)")
    apparent_temperature_max: List[float] = Field(..., description="Daily max feels-like (°C)")
    apparent_temperature_min: List[float] = Field(..., description="Daily min feels-like (°C)")
    precipitation_sum: List[float] = Field(..., description="Total daily precipitation (mm)")
    precipitation_probability_max: List[Optional[int]] = Field(
        ..., description="Max precipitation probability for the day (%)"
    )
    weather_code: List[int] = Field(..., description="Daily WMO weather code")
    wind_speed_10m_max: List[float] = Field(..., description="Daily max wind speed (km/h)")
    wind_gusts_10m_max: List[float] = Field(..., description="Daily max wind gusts (km/h)")
    sunrise: List[str] = Field(..., description="Sunrise ISO-8601 timestamps")
    sunset: List[str] = Field(..., description="Sunset ISO-8601 timestamps")


# ---------------------------------------------------------------------------
# Top-level envelope
# ---------------------------------------------------------------------------

class WeatherResponse(BaseModel):
    latitude: float = Field(..., description="Latitude used for the query")
    longitude: float = Field(..., description="Longitude used for the query")
    timezone: str = Field(..., description="Timezone name (e.g. 'Asia/Kolkata')")
    elevation: float = Field(..., description="Ground elevation at the queried point (m)")
    current: CurrentWeather
    hourly: HourlyForecast
    daily: DailyForecast
    cached: bool = Field(False, description="True if this response was served from the in-memory cache")
