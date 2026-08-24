"""
Pydantic schemas for the /api/chat endpoint.

Intent categories (for docstring reference — used by the orchestrator's
system prompt; will be extended in Section 7):
  - current_weather   : "What's the weather like in Noida right now?"
  - forecast          : "What will the weather be like this week in Delhi?"
  - rain_query        : "Will it rain tomorrow evening in Noida?"
  - travel_advisory   : "Is it a good time to visit Goa this weekend?"
  - farmer_advisory   : "Should I water my crops in Lucknow tomorrow?"
  - alert_query       : (Section 7) "Any severe weather warnings near Mumbai?"
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural-language weather question from the user.",
        examples=["Will it rain tomorrow evening in Noida?"],
    )


class ToolCall(BaseModel):
    """Records a single tool invocation made during the LLM reasoning loop."""
    tool_name: str = Field(..., description="Name of the tool that was called")
    arguments: Dict[str, Any] = Field(..., description="Arguments passed to the tool")
    result_summary: str = Field(..., description="Brief human-readable summary of the tool result")


class ChatResponse(BaseModel):
    answer: str = Field(
        ...,
        description=(
            "Natural-language answer grounded in real weather data. "
            "The LLM is constrained to only use numbers returned by our tools."
        ),
    )
    data_used: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "The raw weather / location data that backed the answer, "
            "keyed by tool name. Enables full transparency and credibility auditing."
        ),
    )
    tool_calls_made: List[ToolCall] = Field(
        default_factory=list,
        description="Ordered list of every tool the LLM invoked during reasoning.",
    )
    model: Optional[str] = Field(
        None,
        description="Groq model identifier used to generate the answer.",
    )
