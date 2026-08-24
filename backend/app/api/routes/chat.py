"""
Chat API router — POST /api/chat

Accepts a natural-language weather question, runs the full agentic
tool-calling loop via the orchestrator, and returns a grounded answer
plus the raw data and tool-call audit trail that backed it.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.db.supabase_client import get_supabase_client
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageRecord,
    ChatRequest,
    ChatResponse,
)
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
        "trail of every tool call made — so you can verify no numbers were invented. "
        "Persists conversation history to Supabase."
    ),
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Ask a natural-language weather question and get a grounded answer.
    """
    logger.info("Chat request: %r", request.message)

    session_id = request.session_id or str(uuid.uuid4())

    # Ensure session exists & save user message
    try:
        supabase = get_supabase_client()
        sess_res = supabase.table("chat_sessions").select("id").eq("id", session_id).execute()
        if not sess_res.data:
            supabase.table("chat_sessions").insert({"id": session_id}).execute()

        supabase.table("chat_messages").insert({
            "session_id": session_id,
            "role": "user",
            "content": request.message,
        }).execute()
    except Exception as exc:
        logger.warning("Supabase chat message write (user turn) failed: %s", exc)

    try:
        response = await answer_weather_question(request.message, language=request.language)
        response.session_id = session_id


        logger.info(
            "Chat answered via %d tool call(s) using model %s",
            len(response.tool_calls_made),
            response.model,
        )

        # Save assistant response
        try:
            supabase = get_supabase_client()
            supabase.table("chat_messages").insert({
                "session_id": session_id,
                "role": "assistant",
                "content": response.answer,
            }).execute()
        except Exception as exc:
            logger.warning("Supabase chat message write (assistant turn) failed: %s", exc)

        return response

    except RuntimeError as exc:
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
        logger.exception("Unexpected error during chat: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again.",
        ) from exc


@router.get(
    "/history",
    response_model=ChatHistoryResponse,
    summary="Get recorded chat history",
    description="Fetch recorded conversation history from Supabase chat_messages table.",
)
async def get_chat_history(
    session_id: Optional[str] = None, limit: int = 50
) -> ChatHistoryResponse:
    """Return all persisted chat messages for a session (or all recent messages)."""
    try:
        supabase = get_supabase_client()
        query = supabase.table("chat_messages").select("*")
        if session_id:
            query = query.eq("session_id", session_id)
        res = query.order("created_at", desc=False).limit(limit).execute()

        records = []
        if res.data:
            for r in res.data:
                records.append(
                    ChatMessageRecord(
                        id=str(r["id"]),
                        session_id=str(r["session_id"]),
                        role=r["role"],
                        content=r["content"],
                        created_at=str(r.get("created_at", "")),
                    )
                )
        return ChatHistoryResponse(messages=records)
    except Exception as exc:
        logger.warning("Failed to fetch chat history from Supabase: %s", exc)
        return ChatHistoryResponse(messages=[])


