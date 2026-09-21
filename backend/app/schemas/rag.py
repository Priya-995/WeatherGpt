"""
Pydantic schemas for the RAG layer and Grounded Advisories.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class GuidanceChunk(BaseModel):
    """Chunk of retrieved knowledge with document metadata."""
    content: str = Field(..., description="Text content of the retrieved chunk")
    title: str = Field(..., description="Document title")
    source_name: str = Field(..., description="Authoritative organization name")
    source_url: str = Field(..., description="Official document URL")


class AdvisorySource(BaseModel):
    """Source attribution for grounded advisory."""
    title: str = Field(..., description="Document title")
    source_name: str = Field(..., description="Organization name")
    source_url: str = Field(..., description="Source web URL")


class GroundedAdvisory(BaseModel):
    """LLM-generated advisory grounded in official guidance documents."""
    headline: str = Field(..., description="Clear action directive headline")
    recommended_action: str = Field(..., description="Detailed grounded safety recommendation")
    why: List[str] = Field(
        default_factory=list,
        description="Key supporting facts/numbers from risk telemetry and official guidance"
    )
    sources: List[AdvisorySource] = Field(
        default_factory=list,
        description="List of official source documents supporting this advisory"
    )
