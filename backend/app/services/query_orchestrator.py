"""
Query Orchestrator — the agentic tool-calling loop.

Flow
----
1. Build the initial message list with system prompt + user question.
2. Send to Groq with our tool definitions.
3. If Groq responds with tool_calls:
     a. Execute each requested tool against our REAL backend services.
     b. Append the tool result(s) back as "tool" role messages.
     c. Loop — send the updated message list back to Groq.
4. When Groq responds with plain text (no more tool calls): done.
5. Return the final answer, all raw data collected, and an audit trail
   of every tool call made.

Safety
------
- MAX_TOOL_ROUNDS prevents an infinite loop if the model keeps requesting
  tools without converging.
- The orchestrator NEVER lets tool exceptions bubble to the LLM as raw
  Python tracebacks — it serialises them as JSON error objects so the LLM
  can respond gracefully (e.g. "I couldn't retrieve data for that location").
- All weather numbers injected into the conversation come exclusively from
  actual tool returns — the LLM has no way to invent data.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Tuple

from app.schemas.chat import ChatResponse, ToolCall
from app.services.groq_service import (
    DEFAULT_MODEL,
    MAX_TOKENS,
    TOOL_DEFINITIONS,
    get_groq_client,
    get_system_prompt,
)

from app.services.location_service import GeocodingServiceError, geocode
from app.services.weather_service import WeatherServiceError, get_forecast
from app.services.advisory_engine import generate_advisories
from app.services.risk_engine import calculate_risk

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6  # safety cap on back-and-forth iterations


# ---------------------------------------------------------------------------
# Tool dispatcher  — maps LLM tool names → real backend coroutines
# ---------------------------------------------------------------------------

async def _execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    data_used: Dict[str, Any],
    tool_calls_made: List[ToolCall],
) -> str:
    """
    Execute the named tool with the given arguments.
    Returns a JSON string to be sent back to the LLM as a tool result.
    Updates data_used and tool_calls_made in-place for audit purposes.
    """
    result_payload: Any

    try:
        if tool_name == "search_location":
            query: str = arguments["query"]
            locations = await geocode(query)

            if not locations:
                result_payload = {"locations": [], "message": f"No locations found for '{query}'."}
                summary = f"No results for '{query}'"
            else:
                result_payload = {
                    "locations": [loc.model_dump() for loc in locations],
                    "count": len(locations),
                }
                top = locations[0]
                summary = (
                    f"Found {len(locations)} result(s). "
                    f"Top: {top.name}, {top.country} "
                    f"(lat={top.latitude}, lon={top.longitude})"
                )

            data_used["search_location"] = result_payload

        elif tool_name == "get_weather":
            lat: float = float(arguments["lat"])
            lon: float = float(arguments["lon"])
            forecast = await get_forecast(lat, lon)

            # Store full raw payload in data_used for UI transparency
            data_used["get_weather"] = forecast.model_dump()

            # Compact payload for LLM context to prevent rate-limit token bloat
            result_payload = {
                "latitude": forecast.latitude,
                "longitude": forecast.longitude,
                "timezone": forecast.timezone,
                "current": forecast.current.model_dump(),
                "hourly_next_24h": {
                    "time": forecast.hourly.time[:24],
                    "temperature": forecast.hourly.temperature_2m[:24],
                    "precipitation": forecast.hourly.precipitation[:24],
                    "precipitation_probability": forecast.hourly.precipitation_probability[:24],
                    "wind_speed": forecast.hourly.wind_speed_10m[:24],
                },
                "daily_7day": {
                    "time": forecast.daily.time,
                    "temp_max": forecast.daily.temperature_2m_max,
                    "temp_min": forecast.daily.temperature_2m_min,
                    "precipitation_sum": forecast.daily.precipitation_sum,
                    "precipitation_probability_max": forecast.daily.precipitation_probability_max,
                    "wind_speed_max": forecast.daily.wind_speed_10m_max,
                },
            }
            summary = (
                f"Retrieved weather for ({lat}, {lon}): "
                f"current temp {forecast.current.temperature_2m}°C, "
                f"humidity {forecast.current.relative_humidity_2m}%, "
                f"precipitation {forecast.current.precipitation}mm"
            )


        elif tool_name == "get_risk":
            lat = float(arguments["lat"])
            lon = float(arguments["lon"])
            forecast = await get_forecast(lat, lon)
            from app.services.alert_service import get_alert_data_for_risk_engine
            alert_data = get_alert_data_for_risk_engine(lat, lon)
            temp_result = calculate_risk(forecast, alert_data=alert_data)
            advisory = generate_advisories(forecast, risk_level=temp_result.level, alert_data=alert_data)
            risk_result = calculate_risk(forecast, alert_data=alert_data, advisory=advisory)

            result_payload = risk_result.model_dump()
            summary = (
                f"Risk level: {risk_result.level.value} "
                f"(score={risk_result.score:.2f}). "
                f"Active advisories: {len(risk_result.advisory.items)}. "
                f"Summary: {risk_result.advisory.summary}"
            )
            data_used["get_risk"] = result_payload

        else:
            result_payload = {"error": f"Unknown tool: {tool_name}"}
            summary = f"Unknown tool '{tool_name}'"

    except (WeatherServiceError, GeocodingServiceError) as exc:
        result_payload = {"error": str(exc)}
        summary = f"Tool error: {exc}"
        logger.warning("Tool %s error: %s", tool_name, exc)

    except (KeyError, TypeError, ValueError) as exc:
        result_payload = {"error": f"Invalid tool arguments: {exc}"}
        summary = f"Argument error: {exc}"
        logger.warning("Tool %s argument error: %s", tool_name, exc)

    tool_calls_made.append(
        ToolCall(tool_name=tool_name, arguments=arguments, result_summary=summary)
    )

    return json.dumps(result_payload, default=str)


# ---------------------------------------------------------------------------
# Main orchestration entry point
# ---------------------------------------------------------------------------

async def answer_weather_question(
    user_message: str, language: str = "en"
) -> ChatResponse:
    """
    Run the full agentic loop for a user weather question.

    1. Sends the question to Groq with tool definitions and language-specific instructions.
    2. Executes any tool calls against real backend services.
    3. Feeds results back and repeats until Groq gives a final text answer.
    4. Returns a ChatResponse with the answer, raw data, tool audit trail, and language.

    Raises OrchestratorError for non-recoverable failures (e.g. missing API key,
    Groq API error, loop exceeded).
    """
    client = get_groq_client()

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": get_system_prompt(language)},
        {"role": "user", "content": user_message},
    ]

    data_used: Dict[str, Any] = {}
    tool_calls_made: List[ToolCall] = []

    for round_num in range(MAX_TOOL_ROUNDS):
        logger.debug("Orchestrator round %d — sending %d messages", round_num + 1, len(messages))

        response = await client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,  # type: ignore[arg-type]
            tools=TOOL_DEFINITIONS,  # type: ignore[arg-type]
            tool_choice="auto",
            max_tokens=MAX_TOKENS,
        )

        choice = response.choices[0]
        msg = choice.message

        # ── Groq returned tool call(s) ──────────────────────────────────────
        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            # Append the assistant's "I want to call tools" turn
            assistant_turn: Dict[str, Any] = {"role": "assistant", "content": msg.content}
            if msg.tool_calls:
                assistant_turn["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]
            messages.append(assistant_turn)


            # Execute all requested tools (Groq can request multiple at once)
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                logger.info("Executing tool: %s(%s)", tool_name, arguments)

                tool_result = await _execute_tool(
                    tool_name, arguments, data_used, tool_calls_made
                )

                # Append the tool result for Groq to read
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })

            # Loop back — let Groq decide if it needs more tools or can answer
            continue

        # ── Groq gave a final text answer ───────────────────────────────────
        final_answer = (msg.content or "").strip()

        if not final_answer:
            final_answer = (
                "I was unable to generate a response. "
                "Please check your question and try again."
            )

        return ChatResponse(
            answer=final_answer,
            data_used=data_used,
            tool_calls_made=tool_calls_made,
            model=response.model,
            language=language,
        )


    # If we exit the loop without a text answer, something went wrong
    raise OrchestratorError(
        f"LLM did not produce a final answer within {MAX_TOOL_ROUNDS} rounds. "
        "This may indicate an issue with the model or tool definitions."
    )


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class OrchestratorError(Exception):
    """Raised when the orchestration loop fails to produce an answer."""
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code
