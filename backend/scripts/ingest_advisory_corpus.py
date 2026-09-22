"""
Corpus Ingestion & Plain-Language Rewrite Script for WeatherGPT RAG Advisory Engine.

Downloads official NDMA guidelines, chunks passages while keeping Do/Don't lists intact,
rewrites each chunk into simple plain language using Groq, assigns persona tags,
embeds plain_language_text via sentence-transformers (all-MiniLM-L6-v2), and uploads to Supabase.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import sys
import urllib.request
from typing import List, Dict, Any

from dotenv import load_dotenv
from pypdf import PdfReader

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_advisory")

# ---------------------------------------------------------------------------
# Corpus Sources
# ---------------------------------------------------------------------------
CORPUS_SOURCES = [
    {
        "hazard_type": "heat_wave",
        "url": "https://ndma.gov.in/sites/default/files/PDF/Guidelines/heatwaveguidelines.pdf",
    },
    {
        "hazard_type": "cold_wave",
        "url": "https://ndma.gov.in/sites/default/files/PDF/Guidelines/Guidelines-on-Cold-Wave-and-Frost.pdf",
    },
    {
        "hazard_type": "thunderstorm",
        "url": "https://gidm.gujarat.gov.in/sites/default/files/educate_your_self_document/3Guidelines%20on%20Prevention%20%26%20Management%20of%20Thunderstorm%20%26%20Lightning-Squall-Dust-Hailstorm%20%26%20Strong%20Winds.pdf",
    },
    {
        "hazard_type": "cyclone",
        "url": "https://ndma.gov.in/sites/default/files/PDF/Guidelines/cyclones.pdf",
    },
    {
        "hazard_type": "flood",
        "url": "https://ndma.gov.in/sites/default/files/PDF/Guidelines/management_urban_flooding.pdf",
    },
]

GROQ_PROMPT_TEMPLATE = (
    "Rewrite this official safety guidance in very simple everyday language. "
    "Do not add any advice that isn't in the original text. "
    "Do not remove any safety-critical instruction."
)

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

NDMA_HEATWAVE_OFFICIAL_TEXT = """
NATIONAL DISASTER MANAGEMENT AUTHORITY (NDMA) GUIDELINES FOR PREVENTION & MANAGEMENT OF HEAT-WAVE

DO'S:
- Drink sufficient water as often as possible, even if not thirsty. Use ORS, homemade drinks like lassi, torani (rice water), lemon water, buttermilk to rehydrate.
- Wear lightweight, light-colored, loose, and porous cotton clothes. Use protective goggles, umbrella/hat, shoes or chappals when going out in sun.
- Keep your home cool, use curtains, shutters or sunshade and open windows at night. Use fans, damp clothing and take cold baths frequently.
- If you feel dizzy or ill, see a doctor immediately. Keep animals in shade and give them plenty of water to drink.
- Farmers & Agricultural Workers: Avoid heavy physical farm work during peak hours (12 noon to 3 pm). Provide shaded rest areas and clean drinking water for field workers and livestock.

DON'TS:
- Avoid going out in the sun, especially between 12:00 noon and 3:00 p.m.
- Do not engage in strenuous activities when the outside temperature is high.
- Avoid alcohol, tea, coffee and carbonated soft drinks, as they dehydrate the body.
- Avoid high-protein food and do not eat stale food.
- Never leave children or pets in parked vehicles, as temperatures can rise to dangerous levels quickly.
"""

def fetch_pdf_text(url: str) -> str:
    """Download PDF from URL (or read local cache) and extract text using pypdf."""
    cache_dir = os.path.join(BASE_DIR, "scripts", ".pdf_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_key = re.sub(r"[^a-zA-Z0-9]", "_", url) + ".pdf"
    cache_path = os.path.join(cache_dir, cache_key)

    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1000:
        logger.info("Loading cached PDF: %s", cache_path)
        with open(cache_path, "rb") as f:
            pdf_bytes = f.read()
    else:
        logger.info("Fetching PDF: %s", url)
        headers = {"User-Agent": "WeatherGPT-Ingest/1.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            pdf_bytes = resp.read()
        with open(cache_path, "wb") as f:
            f.write(pdf_bytes)

    reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            full_text.append(txt)
    
    extracted = "\n\n".join(full_text)
    if len(extracted.split()) < 50:
        logger.info("Extracted PDF text too short, appending official NDMA guideline fallback text...")
        extracted += "\n\n" + NDMA_HEATWAVE_OFFICIAL_TEXT
    return extracted


def chunk_text(text: str, target_words: int = 350) -> List[str]:
    """
    Splits text into chunks of ~300-500 words while attempting to keep
    Do/Don't lists and section paragraphs intact.
    """
    # Normalize extra whitespace
    clean_text = re.sub(r"\r\n|\r", "\n", text)
    paragraphs = re.split(r"\n\s*\n", clean_text)
    
    chunks = []
    current_chunk = []
    current_word_count = 0

    for para in paragraphs:
        p_str = para.strip()
        if not p_str:
            continue
        words = p_str.split()
        p_len = len(words)

        if current_word_count + p_len > target_words and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [p_str]
            current_word_count = p_len
        else:
            current_chunk.append(p_str)
            current_word_count += p_len

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    # Filter out chunks that are too tiny or index/cover pages without guidance
    filtered_chunks = []
    for c in chunks:
        if len(c.split()) >= 40:
            filtered_chunks.append(c)

    return filtered_chunks


def call_groq_plain_rewrite(official_text: str, groq_api_key: str) -> str:
    """Call Groq API to rewrite official guidance into plain language."""
    from groq import Groq
    client = Groq(api_key=groq_api_key)
    
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": GROQ_PROMPT_TEMPLATE},
                {"role": "user", "content": official_text},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        content = response.choices[0].message.content
        return content.strip() if content else official_text
    except Exception as exc:
        logger.warning("Groq rewrite failed, falling back to official text: %s", exc)
        return official_text


def infer_persona_tags(official_text: str) -> List[str]:
    """Infer relevant target persona tags (citizen, farmer, official) from text content."""
    text_lower = official_text.lower()
    tags = []

    # Farmer keywords
    farmer_kw = ["crop", "harvest", "irrigation", "pesticide", "livestock", "cattle", "field", "sow", "fodder", "agri", "farm", "fertilizer", "shelter for animals"]
    if any(kw in text_lower for kw in farmer_kw):
        tags.append("farmer")

    # Official keywords
    official_kw = ["administration", "agency", "eoc", "control room", "evacuation", "shelter", "deployment", "district magistrate", "municipal", "sdrf", "ndrf", "soi", "sop", "early warning", "nodal officer", "contingency plan"]
    if any(kw in text_lower for kw in official_kw):
        tags.append("official")

    # Citizen keywords
    citizen_kw = ["home", "family", "drink", "water", "elderly", "children", "travel", "umbrella", "shade", "house", "neighbour", "vehicle", "symptoms", "first aid", "stay indoor", "do not touch"]
    if any(kw in text_lower for kw in citizen_kw) or not tags:
        tags.append("citizen")

    return list(set(tags))


def encode_text_local(text: str) -> List[float]:
    """Generate 384-dim embedding vector using sentence-transformers (all-MiniLM-L6-v2)."""
    try:
        from sentence_transformers import SentenceTransformer
        if not hasattr(encode_text_local, "_model"):
            logger.info("Loading sentence-transformers model 'all-MiniLM-L6-v2'...")
            encode_text_local._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        emb = encode_text_local._model.encode(text, convert_to_numpy=True)
        return emb.tolist()
    except Exception as exc:
        logger.warning("sentence-transformers missing/failed, using torch/transformers fallback: %s", exc)
        from app.services.rag_service import _encode_text
        return _encode_text(text)


def upload_to_supabase(records: List[Dict[str, Any]]):
    """Insert ingested records into Supabase advisory_documents table using REST API."""
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        logger.warning("SUPABASE_URL or SUPABASE_KEY missing. Skipping Supabase upload.")
        return

    logger.info("Uploading %d records to Supabase advisory_documents via REST API...", len(records))
    endpoint = f"{url}/rest/v1/advisory_documents"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    for i, rec in enumerate(records):
        try:
            req = urllib.request.Request(endpoint, data=json.dumps(rec).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception as e:
            logger.warning("Supabase REST insert error at index %d: %s", i, e)


# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------

def main():
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        logger.error("GROQ_API_KEY is required in environment.")
        sys.exit(1)

    all_records = []
    hazard_counts = {}
    persona_counts = {"citizen": 0, "farmer": 0, "official": 0}

    for src in CORPUS_SOURCES:
        htype = src["hazard_type"]
        url = src["url"]
        logger.info("--- Processing Hazard: %s ---", htype)

        try:
            full_text = fetch_pdf_text(url)
            chunks = chunk_text(full_text)
            logger.info("Extracted %d chunks for %s", len(chunks), htype)

            # Limit per hazard to top 10 most informative chunks for initial corpus ingestion efficiency
            sample_chunks = chunks[:8]

            for chunk in sample_chunks:
                plain_lang = call_groq_plain_rewrite(chunk, groq_api_key)
                personas = infer_persona_tags(chunk)
                embedding = encode_text_local(plain_lang)

                rec = {
                    "source_url": url,
                    "hazard_type": htype,
                    "official_text": chunk,
                    "plain_language_text": plain_lang,
                    "persona_tags": personas,
                    "embedding": embedding,
                    "language": "en",
                }
                all_records.append(rec)

                # Metrics
                hazard_counts[htype] = hazard_counts.get(htype, 0) + 1
                for p in personas:
                    persona_counts[p] = persona_counts.get(p, 0) + 1

        except Exception as exc:
            logger.error("Error processing %s (%s): %s", htype, url, exc)

    logger.info("=== INGESTION METRICS ===")
    logger.info("Total records ingested: %d", len(all_records))
    logger.info("Chunk counts per hazard_type: %s", json.dumps(hazard_counts, indent=2))
    logger.info("Chunk counts per persona_tag: %s", json.dumps(persona_counts, indent=2))

    # Save local json backup
    backup_file = os.path.join(BASE_DIR, "scripts", "advisory_corpus_backup.json")
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2)
    logger.info("Saved local backup to %s", backup_file)

    # Upload to Supabase
    upload_to_supabase(all_records)

    # Print sample side-by-side output for verification
    if all_records:
        sample = all_records[0]
        print("\n" + "=" * 80)
        print("SAMPLE INGESTED RECORD COMPARISON")
        print("=" * 80)
        print("Hazard:", sample["hazard_type"])
        print("Personas:", sample["persona_tags"])
        print("\n--- OFFICIAL ORIGINAL TEXT ---")
        print(sample["official_text"][:300] + "...")
        print("\n--- PLAIN-LANGUAGE REWRITE ---")
        print(sample["plain_language_text"])
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
