# WeatherGPT — AI-powered weather intelligence and early-warning layer

WeatherGPT combines real-time weather data with large language model reasoning to deliver
actionable weather intelligence and early-warning alerts.

## Project structure

| Folder | Purpose |
|--------|---------|
| `frontend/` | Next.js 14 + TypeScript + Tailwind CSS — user-facing web application |
| `backend/`  | Python FastAPI — REST API, LLM orchestration, and data pipeline |

## Quick start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://localhost:8000/health
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

## Environment variables
Copy each `.env.example` to `.env` and fill in the real values before running.
