import logging
from typing import Optional
from app.core.cache import ServiceCache
from app.core.http import get_json
from app.schemas.geo import Place

logger = logging.getLogger(__name__)

# Cache for 24 hours (86400 seconds)
geo_cache = ServiceCache(maxsize=500, ttl=86400)


async def search_places(
    query: str,
    limit: int = 5,
    country: Optional[str] = "IN",
    language: str = "en"
) -> list[Place]:
    country_str = country.strip() if country else ""
    cache_key = f"geo:{query.strip().lower()}:{limit}:{country_str.lower()}:{language.lower()}"

    cached_places = geo_cache.get(cache_key)
    if cached_places is not None:
        logger.debug(f"Cache hit for geocoding query '{query}' (lang={language}, country={country_str})")
        return cached_places

    params = {
        "name": query,
        "count": limit,
        "language": language,
        "format": "json",
    }
    if country_str:
        params["countryCode"] = country_str

    url = "https://geocoding-api.open-meteo.com/v1/search"
    data = await get_json(url, params=params, service_name="Open-Meteo Geocoding")

    raw_results = data.get("results") or []
    places = [Place.model_validate(p) for p in raw_results]

    geo_cache.set(cache_key, places)
    return places
