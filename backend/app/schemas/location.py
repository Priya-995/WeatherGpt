"""
Pydantic schema for a single geocoding result.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Location(BaseModel):
    id: int = Field(..., description="Open-Meteo internal location ID")
    name: str = Field(..., description="Place name (e.g. 'Noida')")
    latitude: float = Field(..., description="Latitude (decimal degrees)")
    longitude: float = Field(..., description="Longitude (decimal degrees)")
    country: str = Field(..., description="Country name (e.g. 'India')")
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 country code (e.g. 'IN')")
    admin1: Optional[str] = Field(None, description="State / province (level-1 admin area)")
    admin2: Optional[str] = Field(None, description="District / county (level-2 admin area)")
    admin3: Optional[str] = Field(None, description="Level-3 admin area, if present")
    timezone: Optional[str] = Field(None, description="IANA timezone (e.g. 'Asia/Kolkata')")
    elevation: Optional[float] = Field(None, description="Ground elevation (m)")
    population: Optional[int] = Field(None, description="Population, if available")
    feature_code: Optional[str] = Field(None, description="GeoNames feature code (e.g. 'PPL')")


class LocationSearchResponse(BaseModel):
    query: str = Field(..., description="The original search query")
    count: int = Field(..., description="Number of results returned")
    results: list[Location] = Field(..., description="List of matching locations")
