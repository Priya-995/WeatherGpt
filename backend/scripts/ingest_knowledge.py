"""
Knowledge Document Ingestion Script for WeatherGPT RAG Layer.

Reads 12+ curated safety guidance documents (IMD, NDMA, MoHFW), chunks text into ~200-400 words,
computes 384-dim embeddings via sentence-transformers/all-MiniLM-L6-v2, and populates
Supabase tables (`knowledge_documents` and `knowledge_chunks`).
"""

import os
import sys
from typing import List, Dict, Any
from dotenv import load_dotenv
# Initialise local embedding model
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
print(f"Loading embedding model '{EMBED_MODEL_NAME}'...")
tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL_NAME)
model = AutoModel.from_pretrained(EMBED_MODEL_NAME)


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Compute normalized 384-dim embeddings for a list of texts."""
    inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
    return embeddings.tolist()

RAW_DOCUMENTS: List[Dict[str, Any]] = [
    # --- IMD SOURCES ---
    {
        "title": "IMD Heavy Rainfall Warning Services",
        "source_name": "India Meteorological Department (IMD)",
        "source_url": "https://mausam.imd.gov.in/imd_latest/contents/pdf/pubbrochures/Heavy%20Rainfall%20Warning%20Services.pdf",
        "hazard": "heavy_rain",
        "persona": "citizen",
        "location_scope": "India",
        "published_at": "2024-01-01",
        "raw_content": (
            "India Meteorological Department (IMD) Heavy Rainfall Warning Services & Color Codes:\n"
            "IMD issues four-color coded warnings for heavy rainfall events across India:\n"
            "1. Green (No Warning): No action required. Weather conditions are normal.\n"
            "2. Yellow (Be Updated): Heavy rain expected (64.5 mm to 115.5 mm in 24 hours). Keep track of weather forecasts, exercise caution when travelling in low-lying areas.\n"
            "3. Orange (Be Prepared): Very heavy rain expected (115.6 mm to 204.4 mm in 24 hours). Be prepared for severe traffic disruptions, waterlogging in urban areas, flash flooding near streams, and potential disruption to essential municipal services.\n"
            "4. Red (Take Action): Extremely heavy rain expected (>= 204.5 mm in 24 hours). Extremely high risk of severe flooding, landslides in hilly terrain, collapse of weak structures, and long power outages. Avoid all unnecessary travel, move to safe shelter or elevated ground immediately, and keep emergency kits ready.\n"
            "Safety Action Guidelines: Avoid staying near open drainage channels, under construction sites, or trees. Never cross flooded roads, culverts, or waterlogged subways on foot or in vehicles."
        )
    },
    {
        "title": "IMD Agromet Advisory Services - Farmer Crop Protection",
        "source_name": "India Meteorological Department (IMD) - GKMS",
        "source_url": "https://mausam.imd.gov.in/responsive/agromet_adv_ser_state_current.php",
        "hazard": "heavy_rain",
        "persona": "farmer",
        "location_scope": "India",
        "published_at": "2026-01-15",
        "raw_content": (
            "IMD Agromet Advisory Services (AAS) Guidelines for Field Crops & Irrigation Management:\n"
            "1. Pesticide & Chemical Spraying: Do NOT spray pesticides, insecticides, or crop nutrients when wind speed exceeds 15-20 km/h or when rain probability exceeds 50% within 6-12 hours. Chemical drift reduces spray efficacy and pollutes nearby soil and natural water bodies.\n"
            "2. Irrigation Scheduling: Postpone scheduled irrigation if cumulative rainfall over the next 24-48 hours is forecast to exceed 10-15 mm. Excess moisture promotes fungal disease and root damage.\n"
            "3. Drainage Management: In low-lying agricultural fields, clear field channels and open drainage ditches prior to heavy rainfall events (> 35 mm/24h) to prevent crop lodging, waterlogging, and soil suffocation.\n"
            "4. Harvest Management: If standing mature crops (rice, wheat, pulses, vegetables) are ready for harvest and heavy rain is forecast within 24-48 hours, expedite harvesting immediately and store threshed produce in dry, elevated, moisture-proof godowns."
        )
    },
    {
        "title": "IMD Agromet Advisory SOP for Weather Risk Mitigation",
        "source_name": "IMD Gramin Krishi Mausam Sewa (GKMS)",
        "source_url": "https://mausam.imd.gov.in/imd_latest/contents/pdf/gkms_sop.pdf",
        "hazard": "general",
        "persona": "farmer",
        "location_scope": "India",
        "published_at": "2025-06-01",
        "raw_content": (
            "Standard Operating Procedure for Agricultural Weather Risk Management:\n"
            "Agricultural advisory units evaluate weather parameters twice weekly (Tuesday & Friday) to issue bi-weekly farm advisories.\n"
            "Key Thresholds for Agricultural Action:\n"
            "- High Temperature & Humidity: Provide light and frequent irrigation during morning/evening hours to mitigate heat stress in standing crops. Protect young saplings with shade nets.\n"
            "- Frost / Severe Cold Wave: Apply light evening irrigation to standing crops to raise soil temperature. Burn farm waste on field boundaries to create protective smoke cover.\n"
            "- High Wind / Squall (> 25 km/h): Provide mechanical support / staking to sugarcane, banana plants, and tall horticultural crops to prevent lodging.\n"
            "- Post-Harvest Storage: Store harvested grains on elevated platforms with tarpaulin covers, ensuring zero water contact."
        )
    },
    {
        "title": "IMD Sub-divisional Warning & Alert System",
        "source_name": "India Meteorological Department (IMD)",
        "source_url": "https://mausam.imd.gov.in/imd_latest/contents/subdivisionwise-warning.php",
        "hazard": "cyclone",
        "persona": "citizen",
        "location_scope": "India",
        "published_at": "2026-02-01",
        "raw_content": (
            "IMD Sub-Divisional Weather Warning & Coastal Safety Directives:\n"
            "IMD divides India into 36 meteorological subdivisions for targeted regional warnings.\n"
            "Cyclone Warnings & Stage Directives:\n"
            "1. Pre-Cyclone Watch: Issued 72 hours prior to severe storm formation.\n"
            "2. Cyclone Alert (Yellow): Issued 48 hours prior to expected landfall. Coastal populations should monitor bulletins.\n"
            "3. Cyclone Warning (Orange): Issued 24 hours prior to landfall. Fishermen strictly prohibited from venturing into deep sea; coastal operations suspended.\n"
            "4. Post-Landfall Outlook (Red): Issued 12 hours prior to landfall until storm dissipates. Immediate evacuation of low-lying coastal areas to storm shelters required."
        )
    },

    # --- NDMA SOURCES ---
    {
        "title": "NDMA Flood Safety Do's and Don'ts",
        "source_name": "National Disaster Management Authority (NDMA) - National Flood Guidelines",
        "source_url": "https://ndma.gov.in/sites/default/files/PDF/Guidelines/flood.pdf",
        "hazard": "flood",
        "persona": "citizen",
        "location_scope": "India",
        "published_at": "2025-05-10",
        "raw_content": (
            "NDMA Flood Safety Do's and Don'ts:\n"
            "BEFORE FLOODS:\n"
            "- Ignore rumors; rely only on official weather bulletins broadcast by NDMA, IMD, or local district administration.\n"
            "- Keep an emergency kit ready containing non-perishable food, drinking water, torch, radio, basic medicines, and personal identity documents in a waterproof bag.\n"
            "- Secure home electrical fittings and shut off main electrical switches and gas cylinders if floodwaters approach.\n\n"
            "DURING FLOODS:\n"
            "- Move quickly to high ground or designated relief shelters.\n"
            "- DO NOT walk, swim, or drive through moving floodwaters. Just 15 cm of moving water can knock a person down; 60 cm can carry away a car.\n"
            "- Stay away from downed power lines and submerged electrical poles.\n\n"
            "AFTER FLOODS:\n"
            "- Drink boiled or chemically purified water only.\n"
            "- Do not enter damaged buildings until inspected by structural safety engineers."
        )
    },
    {
        "title": "NDMA Urban Floods Safety & Drainage Guidance",
        "source_name": "National Disaster Management Authority (NDMA) - Urban Flooding Guidelines",
        "source_url": "https://ndma.gov.in/sites/default/files/PDF/Guidelines/management_urban_flooding.pdf",
        "hazard": "flood",
        "persona": "citizen",
        "location_scope": "India",
        "published_at": "2025-07-20",
        "raw_content": (
            "NDMA Urban Floods Precautions & Evacuation Protocol:\n"
            "Urban areas experience accelerated runoff during heavy rainfall due to high impervious surface cover and storm drain saturation.\n"
            "Safety Directives:\n"
            "- Avoid driving into flooded underpasses, basements, or waterlogged subways.\n"
            "- Stay indoor during torrential downpours. Basement offices and underground residential parking must be evacuated if water begins accumulating near entrances.\n"
            "- Keep drainage outlets around residential quarters clear of plastic debris and solid waste.\n"
            "- If trapped in a submerged vehicle, roll down windows immediately before electrical systems short out; climb onto the roof if vehicle fills with water."
        )
    },
    {
        "title": "NDMA Cyclone Disaster Preparedness & Safety Guidelines",
        "source_name": "National Disaster Management Authority (NDMA) - Cyclone Management Guidelines",
        "source_url": "https://ndma.gov.in/sites/default/files/PDF/Guidelines/cyclones.pdf",
        "hazard": "cyclone",
        "persona": "citizen",
        "location_scope": "India",
        "published_at": "2025-09-01",
        "raw_content": (
            "NDMA Cyclone Preparedness Do's and Don'ts:\n"
            "BEFORE CYCLONE:\n"
            "- Check house structure, repair doors and windows, trim overhang tree branches near roofs.\n"
            "- Keep battery-operated radio, emergency lights, dry food, and clean drinking water stocked for at least 72 hours.\n"
            "- Fishermen must keep boats moored in safe harbors and refrain from going out to sea.\n\n"
            "DURING CYCLONE:\n"
            "- Stay indoors inside the strongest part of the house, away from glass windows.\n"
            "- Turn off electrical appliances and main gas supply.\n"
            "- If the 'eye of the cyclone' passes over (sudden calm), DO NOT go outside. Violent winds will return suddenly from the opposite direction.\n\n"
            "AFTER CYCLONE:\n"
            "- Beware of loose electric wires, fallen trees, and sharp debris."
        )
    },
    {
        "title": "NDMA Heat Wave Safety Guidelines & Action Plan",
        "source_name": "National Disaster Management Authority (NDMA) - Heat Wave Guidelines",
        "source_url": "https://ndma.gov.in/sites/default/files/PDF/Guidelines/heatwaveguidelines.pdf",
        "hazard": "heatwave",
        "persona": "citizen",
        "location_scope": "India",
        "published_at": "2025-03-30",
        "raw_content": (
            "NDMA National Heat Wave Safety Advisory & Personal Care Guidelines:\n"
            "Heatwaves occur when ambient temperatures reach 40°C in plains or 30°C in hilly regions, or when departure from normal temperature is 4.5°C to 6.4°C.\n"
            "Key Precautions:\n"
            "1. Hydration: Drink water frequently, even if not thirsty. Consume ORS (Oral Rehydration Solution), home-made drinks like lassi, torani (rice water), lemon water, buttermilk, and coconut water to stay hydrated.\n"
            "2. Outdoor Work Limits: Avoid strenuous outdoor labor between 11:00 AM and 4:00 PM during peak thermal hours. Outdoor workers must take 15-20 minute cooling breaks in shade every hour.\n"
            "3. Dress Code: Wear lightweight, loose-fitting, light-colored cotton clothes. Use sunglasses, umbrellas, hats, or damp cloth head covers when exposed to sun.\n"
            "4. High Risk Groups: Elderly people, young children, pregnant women, and chronic cardiac/renal patients must stay in cool ventilated indoor rooms."
        )
    },
    {
        "title": "NDMA Lightning Safety & Awareness Protocols",
        "source_name": "National Disaster Management Authority (NDMA) - Lightning Safety Portal",
        "source_url": "https://ndma.gov.in/lightning",
        "hazard": "general",
        "persona": "citizen",
        "location_scope": "India",
        "published_at": "2025-06-15",
        "raw_content": (
            "NDMA Lightning & Severe Thunderstorm Safety Directives:\n"
            "Rule of Thumb (30/30 Rule): If time between seeing lightning flash and hearing thunder is less than 30 seconds, take shelter immediately. Stay sheltered for 30 minutes after hearing last thunder clap.\n"
            "Outdoor Precautions:\n"
            "- Never stand under isolated tall trees, metal towers, or telephone poles.\n"
            "- If caught in an open field with no shelter available, adopt the 'lightning crouch': crouch down on balls of feet with feet together, head tucked between knees, hands covering ears. Minimal contact with ground.\n"
            "- Get out of water bodies (ponds, rivers, paddy fields) instantly.\n"
            "Indoor Precautions:\n"
            "- Unplug corded electrical devices. Avoid touching metal pipes, taps, and wire landlines during severe lightning storms."
        )
    },

    # --- MoHFW / NPCCHH SOURCES ---
    {
        "title": "MoHFW Heat Wave Advisory for State Health Departments 2026",
        "source_name": "Ministry of Health and Family Welfare (MoHFW) / NPCCHH",
        "source_url": "https://ncdc.mohfw.gov.in/uploads/pdf/1.%20Heat%20wave%20advisory%20for%20State%20Health%20department_2026.pdf",
        "hazard": "heatwave",
        "persona": "health",
        "location_scope": "India",
        "published_at": "2026-02-10",
        "raw_content": (
            "Ministry of Health & Family Welfare (MoHFW) / National Programme on Climate Change and Human Health (NPCCHH):\n"
            "National Heat-Health Emergency Preparedness Advisory:\n"
            "1. Medical Facility Readiness: Primary Health Centres (PHCs), Community Health Centres (CHCs), and District Hospitals must establish dedicated 'Heat Stroke Treatment Corners' equipped with ice packs, cold water immersion tubs, ORS packets, IV fluids (Normal Saline/Ringer Lactate), and temperature monitors.\n"
            "2. Clinical Diagnosis & Treatment:\n"
            "   - Heat Exhaustion: Symptoms include severe fatigue, dizziness, nausea, profuse sweating, and pale cold clammy skin. Treatment: Move patient to shade, elevate feet, administer oral fluids/ORS.\n"
            "   - Heat Stroke (Medical Emergency): Symptoms include core body temperature > 40°C (104°F), altered mental status, confusion, slurred speech, delirium, hot dry skin or heavy sweating. Treatment: Rapid cooling by ice packing axillae and groin, cold water sponging, immediate transfer to ICU.\n"
            "3. Vulnerable Population Management: Maintain active outreach for outdoor laborers, traffic police, brick kiln workers, elderly living alone, and infants."
        )
    },
    {
        "title": "NPCCHH Climate Change & Public Health Directives",
        "source_name": "National Centre for Disease Control (NCDC) / MoHFW",
        "source_url": "https://www.ncdc.gov.in/centre-for-environmental-occupational-health-climate-change-health/",
        "hazard": "heatwave",
        "persona": "health",
        "location_scope": "India",
        "published_at": "2025-11-01",
        "raw_content": (
            "NCDC NPCCHH Climate Stress & Heat Illness Prevention Directives:\n"
            "Public Health Response for Extreme Heat Events:\n"
            "- Health Surveillance: State health departments must track daily Emergency Department visits for heat-related illness (HRI) and heat stroke admissions.\n"
            "- Emergency Medical Services: Ambulance crews must be supplied with ORS, ice packs, and cooling blankets.\n"
            "- Community Awareness: Distribute advisories in regional languages emphasizing signs of dehydration, heat cramps, heat syncope, and emergency ambulance helpline contacts (108 / 102)."
        )
    },
    {
        "title": "SACHET Pan-Disaster Citizen Safety Directives",
        "source_name": "NDMA SACHET National Disaster Alert Portal",
        "source_url": "https://sachet.ndma.gov.in/DosDont",
        "hazard": "general",
        "persona": "citizen",
        "location_scope": "India",
        "published_at": "2026-01-01",
        "raw_content": (
            "NDMA SACHET National Alert Portal - Standard Safety Instructions:\n"
            "- Always verify alert notifications received via SMS or SACHET mobile application.\n"
            "- Maintain an emergency contact card with district disaster management authority (DDMA) numbers, police (112), fire (101), and ambulance (108).\n"
            "- Follow instructions issued by local authorities regarding evacuation routes and relief shelter locations during weather emergencies."
        )
    }
]


def chunk_text(text: str, target_words: int = 250) -> List[str]:
    """Splits document content into paragraph-based chunks of ~200-400 words."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = []
    current_word_count = 0

    for p in paragraphs:
        words = len(p.split())
        if current_word_count + words > target_words and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [p]
            current_word_count = words
        else:
            current_chunk.append(p)
            current_word_count += words

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def run_ingestion():
    print(f"Starting ingestion for {len(RAW_DOCUMENTS)} documents...")

    docs_inserted = 0
    chunks_inserted = 0

    for doc in RAW_DOCUMENTS:
        doc_payload = {
            "title": doc["title"],
            "source_name": doc["source_name"],
            "source_url": doc["source_url"],
            "hazard": doc["hazard"],
            "persona": doc["persona"],
            "location_scope": doc.get("location_scope", "India"),
            "published_at": doc.get("published_at"),
            "raw_content": doc["raw_content"],
        }

        try:
            existing = supabase.table("knowledge_documents").select("id").eq("title", doc["title"]).execute()
        except Exception as exc:
            if "PGRST205" in str(exc) or "knowledge_documents" in str(exc):
                print("\n" + "=" * 60)
                print("ACTION REQUIRED: Supabase table 'knowledge_documents' not found.")
                print("Please copy and run the SQL migration script located at:")
                print("  supabase/migrations/20260829000001_rag_knowledge_base.sql")
                print("in your Supabase Dashboard -> SQL Editor, then re-run this script.")
                print("=" * 60 + "\n")
                sys.exit(1)
            raise exc
        if existing.data:
            doc_id = existing.data[0]["id"]
            supabase.table("knowledge_chunks").delete().eq("document_id", doc_id).execute()
        else:
            res = supabase.table("knowledge_documents").insert(doc_payload).execute()
            doc_id = res.data[0]["id"]
            docs_inserted += 1

        chunks = chunk_text(doc["raw_content"])
        if not chunks:
            continue

        embeddings = get_embeddings(chunks)

        chunk_rows = []
        for content_text, emb in zip(chunks, embeddings):
            chunk_rows.append({
                "document_id": doc_id,
                "content": content_text,
                "embedding": emb,
            })

        if chunk_rows:
            supabase.table("knowledge_chunks").insert(chunk_rows).execute()
            chunks_inserted += len(chunk_rows)

        print(f"  [+] Ingested '{doc['title']}' -> {len(chunk_rows)} chunk(s)")

    print(f"\n==========================================")
    print(f"INGESTION COMPLETE SUMMARY:")
    print(f"Documents Ingested / Processed: {len(RAW_DOCUMENTS)}")
    print(f"Total Chunks Ingested: {chunks_inserted}")
    print(f"==========================================")


if __name__ == "__main__":
    run_ingestion()
