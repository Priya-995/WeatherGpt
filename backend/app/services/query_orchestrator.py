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
    detect_language,
    get_groq_client,
    get_system_prompt,
)

from app.services.location_service import GeocodingServiceError, geocode
from app.services.weather_service import WeatherServiceError, get_forecast
from app.services.rag_advisory_engine import generate_advisories, ground_advisories, fetch_grounded_documents
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

        elif tool_name == "get_grounded_advisory":
            loc_query: str = arguments["location"]
            hazard: str = arguments.get("hazard", "general")
            persona: str = arguments.get("persona", "citizen")

            locations = await geocode(loc_query)
            if not locations:
                result_payload = {"error": f"Could not find coordinates for location '{loc_query}'."}
                summary = f"Geocoding failed for '{loc_query}'"
            else:
                top = locations[0]
                lat, lon = top.latitude, top.longitude
                forecast = await get_forecast(lat, lon)

                from app.services.alert_service import get_alert_data_for_risk_engine
                from app.services.rag_advisory_engine import ground_advisories

                alert_data = get_alert_data_for_risk_engine(lat, lon)
                temp_risk = calculate_risk(forecast, alert_data=alert_data)
                advisory_res = generate_advisories(forecast, risk_level=temp_risk.level, alert_data=alert_data)

                # Ground advisories via RAG + Groq synthesis
                grounded_res = await ground_advisories(
                    advisory_res,
                    weather=forecast,
                    risk_level=temp_risk.level,
                    location_name=top.name,
                )

                # Filter items relevant to requested persona/context
                items_payload = []
                all_sources = []
                seen_urls = set()

                for item in grounded_res.items:
                    item_ctx = item.context.lower()
                    # If farmer persona requested, exclude non-farming health heat items
                    if persona and persona.lower() == "farmer":
                        if "heat" in item_ctx and "farmer" not in item_ctx and "agri" not in item_ctx:
                            continue
                    # If health persona requested, exclude general farming items
                    elif persona and persona.lower() in ("health", "medical"):
                        if "farmer" in item_ctx or "agri" in item_ctx:
                            continue

                    item_dict = item.model_dump()
                    items_payload.append(item_dict)
                    if item.grounded and item.grounded.sources:
                        for s in item.grounded.sources:
                            if s.source_url not in seen_urls:
                                seen_urls.add(s.source_url)
                                all_sources.append(s.model_dump())

                result_payload = {
                    "location_name": top.name,
                    "latitude": lat,
                    "longitude": lon,
                    "risk_level": temp_risk.level.value,
                    "hazard": hazard,
                    "persona": persona,
                    "items": items_payload,
                    "sources": all_sources,
                    "summary": grounded_res.summary,
                }

                summary = (
                    f"Retrieved RAG-grounded advisory for {top.name} "
                    f"(persona={persona}, hazard={hazard}): "
                    f"Risk level {temp_risk.level.value}, "
                    f"{len(items_payload)} item(s), "
                    f"{len(all_sources)} official source(s) cited."
                )

                # Store payload in data_used for API output transparency
                data_used["get_grounded_advisory"] = result_payload

                # Build clean tool output text for LLM turn
                formatted_sources = "\n".join([
                    f"- {s['title']} ({s['source_name']}): {s['source_url']}"
                    for s in all_sources
                ])
                formatted_items = "\n".join([
                    f"* [{item.get('context', 'Advisory')}] {item.get('title', '')}: {item.get('message', '')}\n"
                    f"  Action: {item.get('grounded', {}).get('recommended_action', item.get('message', ''))}"
                    for item in items_payload
                ])

                tool_text_output = (
                    f"LOCATION: {top.name} (lat={lat}, lon={lon})\n"
                    f"COMPOSITE RISK LEVEL: {temp_risk.level.value}\n"
                    f"WEATHER TELEMETRY: Max Temp {forecast.daily.temperature_2m_max[0]}°C, "
                    f"Feels Like {forecast.daily.apparent_temperature_max[0]}°C, "
                    f"Rain {forecast.daily.precipitation_sum[0]}mm ({forecast.daily.precipitation_probability_max[0]}% prob), "
                    f"Wind {forecast.daily.wind_speed_10m_max[0]}km/h\n\n"
                    f"GROUNDED ADVISORY DIRECTIVES:\n{formatted_items}\n\n"
                    f"CITED OFFICIAL SOURCES:\n{formatted_sources}"
                )

        elif tool_name == "get_advisory":
            persona: str = arguments.get("persona", "citizen")
            query_text: str = arguments.get("query_text", "")

            docs = fetch_grounded_documents(query_text=query_text, persona=persona, match_count=4)

            retrieved_chunks = [
                {
                    "hazard_type": doc.get("hazard_type"),
                    "plain_language_text": doc.get("plain_language_text"),
                    "official_text": doc.get("official_text"),
                    "source_url": doc.get("source_url"),
                    "persona_tags": doc.get("persona_tags"),
                }
                for doc in docs
            ]

            result_payload = {
                "persona": persona,
                "query_text": query_text,
                "retrieved_chunks": retrieved_chunks,
                "count": len(retrieved_chunks),
            }

            summary = f"Retrieved {len(retrieved_chunks)} grounded NDMA chunk(s) for persona '{persona}'"
            data_used["get_advisory"] = result_payload

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

    if tool_name == "get_grounded_advisory" and "tool_text_output" in locals():
        return tool_text_output

    return json.dumps(result_payload, default=str)


# ---------------------------------------------------------------------------
# Main orchestration entry point
# ---------------------------------------------------------------------------

async def answer_weather_question(
    user_message: str, language: str = "auto"
) -> ChatResponse:
    """
    Run the full agentic loop for a user weather question.

    1. Sends the question to Groq with tool definitions and language-specific instructions.
    2. Executes any tool calls against real backend services.
    3. Feeds results back and repeats until Groq gives a final text answer.
    4. Returns a ChatResponse with the answer, raw data, tool audit trail, and detected language.

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

        # Determine resolved language identifier
        resolved_language = language
        if (not language) or language.lower().strip() in ("auto", "detect", "auto-detect", "default"):
            detected_from_ans = detect_language(final_answer)
            detected_from_user = detect_language(user_message)
            if detected_from_ans != "en":
                resolved_language = detected_from_ans
            elif detected_from_user != "en":
                resolved_language = detected_from_user
            else:
                resolved_language = "en"

        # Extract sources from get_grounded_advisory or get_risk if present
        extracted_sources = []
        if "get_grounded_advisory" in data_used and "sources" in data_used["get_grounded_advisory"]:
            extracted_sources = data_used["get_grounded_advisory"]["sources"]
        elif "get_risk" in data_used and "advisory" in data_used["get_risk"]:
            advisory = data_used["get_risk"]["advisory"]
            for item in advisory.get("items", []):
                if item.get("grounded") and item["grounded"].get("sources"):
                    extracted_sources.extend(item["grounded"]["sources"])

        return ChatResponse(
            answer=final_answer,
            data_used=data_used,
            tool_calls_made=tool_calls_made,
            model=response.model,
            language=resolved_language,
            sources=extracted_sources,
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
