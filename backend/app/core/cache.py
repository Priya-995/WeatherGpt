from typing import Any, Optional
from cachetools import TTLCache


class ServiceCache:
    def __init__(self, maxsize: int = 100, ttl: int = 300):
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

    def clear(self) -> None:
        self._cache.clear()

    def __contains__(self, key: str) -> bool:
        return key in self._cache
