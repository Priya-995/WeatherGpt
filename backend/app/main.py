import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()  # loads backend/.env in development; no-op in production

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.alerts import router as alerts_router
from app.api.routes.chat import router as chat_router
from app.api.routes.location import router as location_router
from app.api.routes.risk import router as risk_router
from app.api.routes.weather import router as weather_router
from app.api.routes.websocket import router as websocket_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="WeatherGPT API",
    description="AI-powered weather intelligence and early-warning layer.",
    version="0.1.0",
)

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://weather-gpt-mu.vercel.app",
]

# Enable CORS for frontend clients (Next.js local & Vercel deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _periodic_imd_poller():
    """Background loop polling IMD CAP RSS feed every 10 minutes."""
    while True:
        await asyncio.sleep(600)
        try:
            from app.services.alert_service import fetch_and_store_alerts
            fetch_and_store_alerts()
            logger.info("Periodic IMD CAP alerts feed refresh completed.")
        except Exception as exc:
            logger.warning("Periodic IMD feed refresh failed: %s", exc)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(_periodic_imd_poller())


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"], summary="Health check")
async def health_check():
    return {"status": "ok"}


# ── Feature routers ───────────────────────────────────────────────────────────

app.include_router(weather_router)
app.include_router(location_router)
app.include_router(chat_router)
app.include_router(risk_router)
app.include_router(alerts_router)
app.include_router(websocket_router)
