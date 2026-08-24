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

app = FastAPI(
    title="WeatherGPT API",
    description="AI-powered weather intelligence and early-warning layer.",
    version="0.1.0",
)

# Enable CORS for frontend clients (e.g. Next.js on localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
