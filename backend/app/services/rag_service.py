"""
RAG Service — retrieval of grounded safety guidance from Supabase pgvector database.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from dotenv import load_dotenv
from app.schemas.rag import GuidanceChunk

load_dotenv()

logger = logging.getLogger(__name__)

EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_embedding_components():
    """Lazy-load and cache HuggingFace tokenizer and AutoModel."""
    from transformers import AutoModel, AutoTokenizer
    logger.info("Loading local embedding model '%s'...", EMBED_MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL_NAME)
    model = AutoModel.from_pretrained(EMBED_MODEL_NAME)
    return tokenizer, model


def _encode_text(text: str) -> List[float]:
    """Compute normalized 384-dim embedding vector for text string."""
    try:
        import torch
        tokenizer, model = _get_embedding_components()
        inputs = tokenizer([text], padding=True, truncation=True, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        return embeddings[0].tolist()
    except Exception as exc:
        logger.warning("Local embedding failed (torch/transformers missing or error): %s", exc)
        return [0.0] * 384


@lru_cache(maxsize=1)
def _get_supabase_client() -> Optional[Any]:
    """Lazy-load Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logger.warning("SUPABASE_URL or SUPABASE_KEY not set. RAG retrieval disabled.")
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as exc:
        logger.error("Failed to create Supabase client: %s", exc)
        return None


def retrieve_guidance(
    hazard: str = "general",
    persona: str = "all",
    query_text: str = "",
    match_count: int = 4,
) -> List[GuidanceChunk]:
    """
    Embed query text and invoke Supabase RPC `match_knowledge_chunks`.
    Returns top matching chunks with metadata.
    """
    if not query_text.strip():
        query_text = f"Safety guidance for {hazard} risk facing {persona}"

    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        return []

    try:
        query_embedding = _encode_text(query_text)

        # 1. Try python client if initialized successfully
        client = _get_supabase_client()
        raw_rows = None
        if client:
            try:
                res = client.rpc(
                    "match_knowledge_chunks",
                    {
                        "query_embedding": query_embedding,
                        "match_hazard": hazard,
                        "match_persona": persona,
                        "match_count": match_count,
                    },
                ).execute()
                raw_rows = res.data
            except Exception as e:
                logger.warning("Supabase python SDK client RPC failed: %s", e)

        # 2. Direct HTTP REST fallback if SDK client is unavailable or failed
        if raw_rows is None:
            import json
            import urllib.request
            rpc_url = f"{url}/rest/v1/rpc/match_knowledge_chunks"
            headers = {
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            payload = {
                "query_embedding": query_embedding,
                "match_hazard": hazard,
                "match_persona": persona,
                "match_count": match_count,
            }
            req = urllib.request.Request(rpc_url, data=json.dumps(payload).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw_rows = json.loads(resp.read().decode('utf-8'))

        chunks: List[GuidanceChunk] = []
        for row in raw_rows or []:
            chunks.append(
                GuidanceChunk(
                    content=row.get("content", ""),
                    title=row.get("doc_title", "Official Guidance"),
                    source_name=row.get("doc_source_name", "Government Advisory"),
                    source_url=row.get("doc_source_url", "https://ndma.gov.in"),
                )
            )

        return chunks
    except Exception as exc:
        logger.error("RAG guidance retrieval failed: %s", exc)
        return []
