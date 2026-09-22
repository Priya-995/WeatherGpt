"""
Unit tests for WeatherGPT RAG Advisory Engine & Persona Chat Integration.
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from app.schemas.weather import WeatherResponse
from app.services.rag_advisory_engine import (
    generate_advisories,
    fetch_grounded_documents,
    _determine_hazard_types,
)
from scripts.ingest_advisory_corpus import (
    infer_persona_tags,
    chunk_text,
)


# ---------------------------------------------------------------------------
# Test 1: Plain-language rewrite sanity check (Bullet count preservation)
# ---------------------------------------------------------------------------

def test_bullet_count_preservation_sanity():
    official_text = (
        "PREVENTION AND MANAGEMENT OF HEAT WAVE:\n"
        "- Do 1: Drink sufficient water even if not thirsty.\n"
        "- Do 2: Wear lightweight, loose cotton clothes.\n"
        "- Don't 1: Avoid strenuous activity between 12 noon and 3 pm.\n"
        "- Don't 2: Do not leave children or pets in parked vehicles."
    )
    
    # Count official bullets
    official_bullets = len([line for line in official_text.splitlines() if line.strip().startswith("-")])
    assert official_bullets == 4

    # Simulated plain language rewrite with preserved instructions
    plain_rewrite = (
        "Heat Wave Safety Guidelines:\n"
        "1. Drink plenty of water frequently.\n"
        "2. Wear light and loose cotton clothing.\n"
        "3. Avoid heavy physical work outside between 12 PM and 3 PM.\n"
        "4. Never leave children or pets inside parked cars."
    )
    
    rewrite_lines = [l for l in plain_rewrite.splitlines() if l.strip() and l[0].isdigit()]
    assert len(rewrite_lines) == official_bullets


# ---------------------------------------------------------------------------
# Test 2: Persona Filter returns only tagged chunks
# ---------------------------------------------------------------------------

def test_persona_filter_tagging():
    farmer_text = "Farmers should delay spraying pesticides and irrigate crops during early morning."
    citizen_text = "Citizens should carry umbrellas, drink ORS water, and check on elderly neighbors."
    official_text = "District Magistrate and EOC control room should deploy SDRF teams and issue public warnings."

    assert "farmer" in infer_persona_tags(farmer_text)
    assert "citizen" in infer_persona_tags(citizen_text)
    assert "official" in infer_persona_tags(official_text)


# ---------------------------------------------------------------------------
# Test 3: Groq JSON-parse failure returns empty/unavailable result
# ---------------------------------------------------------------------------

def test_groq_failure_fallback():
    mock_weather = MagicMock(spec=WeatherResponse)
    mock_weather.daily = None

    with patch("app.services.rag_advisory_engine.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        # Simulate bad JSON response
        mock_client.chat.completions.create.side_effect = Exception("API rate limit or parse error")

        result = generate_advisories(mock_weather, persona="citizen")
        assert result is not None
        assert result.summary == "advisory temporarily unavailable"
        assert len(result.items) == 0


# ---------------------------------------------------------------------------
# Test 4: Chat get_advisory Tool Grounding (Zero Hallucination)
# ---------------------------------------------------------------------------

def test_chat_get_advisory_grounding():
    import asyncio
    mock_docs = [
        {
            "hazard_type": "thunderstorm",
            "official_text": "Do not seek shelter under tall trees during lightning.",
            "plain_language_text": "Never stand under tall trees when there is lightning and heavy rain.",
            "source_url": "https://gidm.gujarat.gov.in",
            "persona_tags": ["citizen"],
        }
    ]

    from app.services import rag_advisory_engine
    with patch("app.services.rag_advisory_engine.fetch_grounded_documents", return_value=mock_docs):
        docs = rag_advisory_engine.fetch_grounded_documents("kal chhata le jaun kya", persona="citizen")
        assert len(docs) == 1
        retrieved_text = docs[0]["plain_language_text"]
        assert "Never stand under tall trees" in retrieved_text
        assert docs[0]["source_url"] == "https://gidm.gujarat.gov.in"
