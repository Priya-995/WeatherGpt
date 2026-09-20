from typing import Optional
from pydantic import BaseModel


class Place(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    admin1: Optional[str] = None
    admin2: Optional[str] = None
    admin3: Optional[str] = None
    timezone: Optional[str] = None
    population: Optional[int] = None


class GeocodeResponse(BaseModel):
    query: str
    count: int
    results: list[Place]
