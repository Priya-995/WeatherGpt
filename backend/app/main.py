from fastapi import FastAPI

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
