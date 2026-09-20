import pytest
import httpx
import respx

from app.main import app
from app.services.geocoding import geo_cache


@pytest.fixture(autouse=True)
def clear_geocoding_cache():
    geo_cache.clear()
    yield
    geo_cache.clear()


@pytest.mark.asyncio
@respx.mock
async def test_geocode_normal_result():
    respx.get("https://geocoding-api.open-meteo.com/v1/search").respond(
        status_code=200,
        json={
            "results": [
                {
                    "id": 1271308,
                    "name": "Ghaziabad",
                    "latitude": 28.66535,
                    "longitude": 77.43915,
                    "elevation": 214.0,
                    "country_code": "IN",
                    "country": "India",
                    "admin1": "Uttar Pradesh",
                    "admin2": "Ghaziabad",
                    "timezone": "Asia/Kolkata",
                    "population": 1199191,
                }
            ]
        }
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/geocode?q=Ghaziabad&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "Ghaziabad"
        assert data["count"] == 1
        assert len(data["results"]) == 1
        place = data["results"][0]
        assert place["id"] == 1271308
        assert place["name"] == "Ghaziabad"
        assert place["admin1"] == "Uttar Pradesh"
        assert place["admin2"] == "Ghaziabad"


@pytest.mark.asyncio
@respx.mock
async def test_geocode_empty_result():
    respx.get("https://geocoding-api.open-meteo.com/v1/search").respond(
        status_code=200,
        json={"generationtime_ms": 0.5}
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/geocode?q=zzzqqxx")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "zzzqqxx"
        assert data["count"] == 0
        assert data["results"] == []


@pytest.mark.asyncio
@respx.mock
async def test_geocode_upstream_500_error():
    respx.get("https://geocoding-api.open-meteo.com/v1/search").respond(
        status_code=500,
        json={"error": True, "reason": "Internal Server Error"}
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/geocode?q=Ghaziabad")
        assert response.status_code == 502
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "UPSTREAM_ERROR"
        assert "message" in data["error"]


@pytest.mark.asyncio
async def test_geocode_query_too_short():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/geocode?q=a")
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "message" in data["error"]


# ── Live Tests ─────────────────────────────────────────────────────────────

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_geocode_english():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/geocode?q=Ghaziabad&limit=5&country=IN&lang=en")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        first_place = data["results"][0]
        assert pytest.approx(first_place["latitude"], abs=0.5) == 28.6
        assert pytest.approx(first_place["longitude"], abs=0.5) == 77.4
        assert first_place["admin1"] == "Uttar Pradesh"


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_geocode_hindi():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/geocode?q=ग़ाज़ियाबाद&limit=5&country=IN&lang=hi")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        assert len(data["results"]) >= 1


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_geocode_no_match():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/geocode?q=zzzqqxx")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["results"] == []
