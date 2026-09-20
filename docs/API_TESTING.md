# WeatherGPT API Testing Guide

## Health Endpoint

### GET /api/v1/health

Check backend server health status and environment parameters.

**Command:**
```bash
curl -X GET http://localhost:8000/api/v1/health
```

**Expected Response (200 OK):**
```json
{
  "status": "ok",
  "app": "WeatherGPT",
  "env": "dev",
  "version": "0.1.0",
  "time_utc": "2026-09-20T18:08:32.000000+00:00"
}
```
