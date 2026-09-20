# WeatherGPT API Testing Guide

## Health Endpoint

### GET /api/v1/health

Check backend server health status and environment parameters.

**Command:**
```powershell
curl.exe -s http://localhost:8000/api/v1/health
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

---

## Geocoding Endpoint

### GET /api/v1/geocode

Convert location names to geographic coordinates with optional country and language filtering.

#### 1. English Search Query
**Command:**
```powershell
curl.exe -s "http://localhost:8000/api/v1/geocode?q=Ghaziabad&limit=5&country=IN&lang=en"
```

**Expected Response (200 OK):**
```json
{
  "query": "Ghaziabad",
  "count": 1,
  "results": [
    {
      "id": 1271308,
      "name": "Ghaziabad",
      "latitude": 28.66535,
      "longitude": 77.43915,
      "elevation": 214.0,
      "country": "India",
      "country_code": "IN",
      "admin1": "Uttar Pradesh",
      "admin2": "Ghaziabad",
      "admin3": "Ghāziābād",
      "timezone": "Asia/Kolkata",
      "population": 1199191
    }
  ]
}
```

#### 2. Hindi Search Query (PowerShell-friendly)
**Command:**
```powershell
curl.exe -s -G "http://localhost:8000/api/v1/geocode" --data-urlencode "q=ग़ाज़ियाबाद" --data-urlencode "limit=5" --data-urlencode "country=IN" --data-urlencode "lang=hi"
```

**Expected Response (200 OK):**
```json
{
  "query": "ग़ाज़ियाबाद",
  "count": 1,
  "results": [
    {
      "id": 1271308,
      "name": "ग़ाज़ियाबाद",
      "latitude": 28.66535,
      "longitude": 77.43915,
      "elevation": 214.0,
      "country": "भारत",
      "country_code": "IN",
      "admin1": "उत्तर प्रदेश",
      "admin2": "Ghāziābād",
      "admin3": "Ghāziābād",
      "timezone": "Asia/Kolkata",
      "population": 1199191
    }
  ]
}
```

#### 3. No Results Match
**Command:**
```powershell
curl.exe -s "http://localhost:8000/api/v1/geocode?q=zzzqqxx"
```

**Expected Response (200 OK):**
```json
{
  "query": "zzzqqxx",
  "count": 0,
  "results": []
}
```

#### 4. Query Too Short (Validation Error)
**Command:**
```powershell
curl.exe -s "http://localhost:8000/api/v1/geocode?q=a"
```

**Expected Response (422 Unprocessable Entity):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "query->q: String should have at least 2 characters"
  }
}
```
