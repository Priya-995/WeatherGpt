"""
Pydantic schemas for the Risk & Advisory API response.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"


class SubScore(BaseModel):
    """Individual severity component contributing to the composite risk score."""
    name: str = Field(..., description="Component name (e.g. 'rainfall_severity')")
    raw_value: float = Field(..., description="The raw meteorological value used")
    unit: str = Field(..., description="Unit of the raw value (e.g. 'mm', 'km/h', '°C')")
    severity: float = Field(..., ge=0.0, le=1.0, description="Normalised severity 0–1")
    weight: float = Field(..., description="Weight applied to this component in the formula")
    weighted: float = Field(..., description="severity × weight")
    threshold_note: str = Field(..., description="Which threshold bucket this value fell into")


class RiskResult(BaseModel):
    """Composite risk assessment for a location."""
    score: float = Field(..., ge=0.0, le=1.0, description="Composite risk score 0–1")
    level: RiskLevel = Field(..., description="Human-readable risk level")
    reasons: List[str] = Field(
        ..., description="Ordered list of plain-English explanations for the score"
    )
    sub_scores: List[SubScore] = Field(
        ..., description="Per-component breakdown of the composite score"
    )
    advisory: "AdvisoryResult" = Field(
        ..., description="Rule-based advisories for citizen, farmer, and heat contexts"
    )


class AdvisoryItem(BaseModel):
    """A single rule-based advisory recommendation."""
    context: str = Field(
        ..., description="Target audience (citizen, farmer, heat)"
    )
    severity: str = Field(
        ..., description="Severity of this advisory (info, warning, danger)"
    )
    title: str = Field(..., description="Short title of the advisory")
    message: str = Field(..., description="Full advisory message")
    triggered_by: List[str] = Field(
        ..., description="Which weather conditions triggered this rule"
    )


class AdvisoryResult(BaseModel):
    """Collection of rule-based advisories across all applicable contexts."""
    items: List[AdvisoryItem] = Field(
        default_factory=list,
        description="All active advisory items (may be empty when risk is Low)"
    )
    summary: Optional[str] = Field(
        None,
        description="One-line overall advisory summary for quick display"
    )
