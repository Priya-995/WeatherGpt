"""
Supabase client initialization module.

Initializes the Supabase client using SUPABASE_URL and SUPABASE_KEY environment variables.
"""

from __future__ import annotations

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "").strip()


_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Return the singleton Supabase Client instance.
    Raises RuntimeError if SUPABASE_URL or SUPABASE_KEY is missing or client creation fails.
    """
    global _client
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()

    if not url or not key:
        logger.error("SUPABASE_URL or SUPABASE_KEY environment variable is missing.")
        raise RuntimeError(
            "Supabase credentials missing. Please set SUPABASE_URL and SUPABASE_KEY in backend/.env"
        )

    try:
        _client = create_client(url, key)
        logger.info("Supabase client successfully initialized.")
        return _client
    except Exception as exc:
        logger.error("Failed to initialize Supabase client: %s", exc)
        raise RuntimeError(f"Could not connect to Supabase: {exc}") from exc
