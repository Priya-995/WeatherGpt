import asyncio
from typing import Any, Optional
import httpx

from app.core.errors import UpstreamError

_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("HTTP client is not initialized")
    return _client


async def init_http_client() -> None:
    global _client
    _client = httpx.AsyncClient(
        timeout=10.0,
        headers={"User-Agent": "WeatherGPT/0.1 (college project)"}
    )


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def get_json(
    url: str,
    params: Optional[dict[str, Any]] = None,
    service_name: str = "upstream"
) -> Any:
    client = get_http_client()
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = await client.get(url, params=params)
            if response.status_code >= 500:
                if attempt < max_retries:
                    await asyncio.sleep(0.2 * (2 ** attempt))
                    continue
                raise UpstreamError(
                    service=service_name,
                    status_code=response.status_code,
                    message=f"Upstream service '{service_name}' returned status {response.status_code}"
                )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            if attempt < max_retries:
                await asyncio.sleep(0.2 * (2 ** attempt))
                continue
            raise UpstreamError(
                service=service_name,
                status_code=504,
                message=f"Timeout contacting upstream service '{service_name}'"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise UpstreamError(
                service=service_name,
                status_code=exc.response.status_code,
                message=f"Upstream service '{service_name}' returned status {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            if attempt < max_retries:
                await asyncio.sleep(0.2 * (2 ** attempt))
                continue
            raise UpstreamError(
                service=service_name,
                status_code=502,
                message=f"Failed to connect to upstream service '{service_name}'"
            ) from exc
