WeatherGPT is an AI-powered weather intelligence and early-warning system for India. Users ask weather questions in English, Hindi or Hinglish. The system combines live weather (Open-Meteo), river discharge (GloFAS via the Open-Meteo Flood API) and official alerts (IMD CAP feed, NDMA SACHET), works out what it means for one specific place, and explains it in plain language.
Later phases: own XGBoost flood/heavy-rain risk model, Groq (Llama 3.3 70B) chat with tool calling, RAG advisory (Supabase pgvector), Next.js frontend, Supabase Postgres database.
Principles:
1. Official warnings are always the final word.
2. The chat layer only uses real fetched data and never invents values.
3. Every external API is wrapped in its own service module so it can be tested and mocked independently.
Stack: Python 3.11+, FastAPI, httpx (async), pydantic v2. Deployment later on Render/Railway.
