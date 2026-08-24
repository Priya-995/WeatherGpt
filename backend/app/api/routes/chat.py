"""
Chat API router — POST /api/chat

Accepts a natural-language weather question, runs the full agentic
tool-calling loop via the orchestrator, and returns a grounded answer
plus the raw data and tool-call audit trail that backed it.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.query_orchestrator import OrchestratorError, answer_weather_question

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask a natural-language weather question",
    description=(
        "Accepts a free-text weather question. The backend runs an agentic "
        "tool-calling loop: it calls our geocoding and weather APIs to retrieve "
        "REAL data, then feeds that data to the LLM to generate a grounded answer. "
        "The response includes the answer, all raw data used, and a full audit "
        "trail of every tool call made — so you can verify no numbers were invented."
    ),
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Ask a natural-language weather question and get a grounded answer.

    **Request body**
    ```json
    { "message": "Will it rain tomorrow evening in Noida?" }
    ```

    **Response**
    - `answer` — the LLM's natural-language response (grounded in real data)
    - `data_used` — raw weather/location data that backed the answer
    - `tool_calls_made` — ordered audit trail of every tool the LLM invoked
    - `model` — Groq model that generated the answer
    """
    logger.info("Chat request: %r", request.message)

    try:
        response = await answer_weather_question(request.message)
        logger.info(
            "Chat answered via %d tool call(s) using model %s",
            len(response.tool_calls_made),
            response.model,
        )
        return response

    except RuntimeError as exc:
        # Raised by get_groq_client() when GROQ_API_KEY is missing
        logger.error("Groq client error: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except OrchestratorError as exc:
        logger.error("Orchestrator error: %s", exc)
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Catch-all — never leak internal tracebacks to the client
        logger.exception("Unexpected error during chat: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again.",
        ) from exc
