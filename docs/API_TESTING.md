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

---

## IMD Official Alerts Endpoint

### GET /api/v1/alerts/imd

Fetch active official weather alerts from IMD CAP feed with optional filters.

#### 1. List All Active Alerts
**Command:**
```powershell
curl.exe -s "http://localhost:8000/api/v1/alerts/imd"
```

**Expected Response (200 OK):**
```json
{
  "source": "IMD",
  "fetched_at": "2026-09-20T18:39:44.395824+00:00",
  "count": 0,
  "skipped": 2,
  "alerts": []
}
```

#### 2. Filter Alerts by State
**Command:**
```powershell
curl.exe -s "http://localhost:8000/api/v1/alerts/imd?state=Odisha"
```

**Expected Response (200 OK):**
```json
{
  "source": "IMD",
  "fetched_at": "2026-09-20T18:39:51.561822+00:00",
  "count": 0,
  "skipped": 2,
  "alerts": []
}
```

#### 3. Alerts by Location Name (q=Ghaziabad)
**Command:**
```powershell
curl.exe -s "http://localhost:8000/api/v1/alerts/imd/by-location?q=Ghaziabad"
```

**Expected Response (200 OK):**
```json
{
  "location": {
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
  },
  "source": "IMD",
  "fetched_at": "2026-09-20T18:39:59.824420+00:00",
  "count": 0,
  "matches": [],
  "note": "No active IMD alert matched this location at fetch time. This is not a guarantee of safety."
}
```

#### 4. Alerts by Coordinates (lat/lon)
**Command:**
```powershell
curl.exe -s "http://localhost:8000/api/v1/alerts/imd/by-location?lat=28.66535&lon=77.43915"
```

**Expected Response (200 OK):**
```json
{
  "location": {
    "id": 0,
    "name": "Coordinates (28.66535, 77.43915)",
    "latitude": 28.66535,
    "longitude": 77.43915,
    "elevation": null,
    "country": null,
    "country_code": null,
    "admin1": null,
    "admin2": null,
    "admin3": null,
    "timezone": null,
    "population": null
  },
  "source": "IMD",
  "fetched_at": "2026-09-20T18:40:08.239344+00:00",
  "count": 0,
  "matches": [],
  "note": "No active IMD alert matched this location at fetch time. This is not a guarantee of safety."
}
```

#### 5. Invalid Latitude (Validation Error)
**Command:**
```powershell
curl.exe -s "http://localhost:8000/api/v1/alerts/imd/by-location?lat=999&lon=77.4"
```

**Expected Response (422 Unprocessable Entity):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "query->lat: Input should be less than or equal to 90"
  }
}
```
