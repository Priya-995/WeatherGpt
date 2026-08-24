from dotenv import load_dotenv

load_dotenv()  # loads backend/.env in development; no-op in production

from fastapi import FastAPI

from app.api.routes.chat import router as chat_router
from app.api.routes.location import router as location_router
from app.api.routes.weather import router as weather_router

app = FastAPI(
    title="WeatherGPT API",
    description="AI-powered weather intelligence and early-warning layer.",
    version="0.1.0",
)

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"], summary="Health check")
async def health_check():
    return {"status": "ok"}


# ── Feature routers ───────────────────────────────────────────────────────────

app.include_router(weather_router)
app.include_router(location_router)
app.include_router(chat_router)
