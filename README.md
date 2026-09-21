# WeatherGPT ⚡ AI-Powered Weather Intelligence & IMD Emergency Alerts

WeatherGPT combines real-time Open-Meteo telemetry, official WMO / IMD CAP emergency alerts, composite risk analysis, and LLM-grounded weather advisories.

---

## 📁 Repository Structure

```text
WeatherGPT/
├── backend/          # FastAPI Python backend (CAP ingest, risk engine, WebSockets)
├── frontend/         # Next.js React frontend (Alert Center, State Selector, Dashboard)
├── docs/             # Application documentation
├── README.md
└── .gitignore
```

---

## 🚀 Getting Started

### 1. Run Backend (FastAPI)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- **Interactive API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **State Weather Alerts:** [http://localhost:8000/api/alerts?state=Uttar%20Pradesh](http://localhost:8000/api/alerts?state=Uttar%20Pradesh)

### 2. Run Frontend (Next.js)

```powershell
cd frontend
npm install
npm run dev
```

- **Frontend App:** [http://localhost:3000](http://localhost:3000)
- **Alert Center & State Selector:** [http://localhost:3000/alerts](http://localhost:3000/alerts)

---

## 🧪 Running Pytest Unit Tests

```powershell
$env:PYTHONPATH="backend"; python -m pytest backend/tests
```
