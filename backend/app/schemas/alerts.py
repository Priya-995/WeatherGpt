from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class AlertArea(BaseModel):
    area_desc: str
    polygons: list[list[tuple[float, float]]] = Field(
        default_factory=list,
        description="List of polygons, where each polygon is a list of (lat, lon) coordinate tuples"
    )
    circles: list[str] = Field(default_factory=list)
    geocodes: list[dict[str, str]] = Field(default_factory=list)


class Alert(BaseModel):
    identifier: str
    sender: str
    sent: datetime
    status: str
    msg_type: str
    scope: str
    event: str
    category: str
    urgency: str
    severity: str
    certainty: str
    effective: Optional[datetime] = None
    onset: Optional[datetime] = None
    expires: Optional[datetime] = None
    headline: Optional[str] = None
    description: Optional[str] = None
    instruction: Optional[str] = None
    link: Optional[str] = None
    areas: list[AlertArea] = Field(default_factory=list)
    references: Optional[str] = None
    source: str = "IMD"


class AlertMatch(BaseModel):
    alert: Alert
    match_method: Literal["polygon", "district", "state"]
    matched_on: str
