from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any


class CacheStore:
    backend_name = "none"

    def get_json(self, key: str) -> Any | None:
        raise NotImplementedError

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        raise NotImplementedError

    def delete_prefix(self, prefix: str) -> None:
        raise NotImplementedError


class NullCacheStore(CacheStore):
    backend_name = "disabled"

    def get_json(self, key: str) -> Any | None:
        return None

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        return

    def delete_prefix(self, prefix: str) -> None:
        return


@dataclass
class InMemoryCacheStore(CacheStore):
    backend_name = "memory"

    def __post_init__(self) -> None:
        self._items: dict[str, tuple[float, str]] = {}

    def get_json(self, key: str) -> Any | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, payload = item
        if expires_at <= time.time():
            self._items.pop(key, None)
            return None
        return json.loads(payload)

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        expires_at = time.time() + max(ttl_seconds, 1)
        self._items[key] = (expires_at, json.dumps(value, ensure_ascii=False))

    def delete_prefix(self, prefix: str) -> None:
        keys = [key for key in self._items if key.startswith(prefix)]
        for key in keys:
            self._items.pop(key, None)


class RedisCacheStore(CacheStore):
    backend_name = "redis"

    def __init__(self, client, prefix: str = "novel2script") -> None:
        self._client = client
        self._prefix = prefix

    def _namespaced(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def get_json(self, key: str) -> Any | None:
        raw = self._client.get(self._namespaced(key))
        if raw is None:
            return None
        return json.loads(raw)

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._client.set(self._namespaced(key), json.dumps(value, ensure_ascii=False), ex=max(ttl_seconds, 1))

    def delete_prefix(self, prefix: str) -> None:
        pattern = self._namespaced(f"{prefix}*")
        keys = list(self._client.scan_iter(match=pattern))
        if keys:
            self._client.delete(*keys)


def build_cache_store(redis_url: str | None, enabled: bool, prefix: str = "novel2script") -> CacheStore:
    if not enabled or not redis_url:
        return NullCacheStore()

    try:
        import redis
    except ImportError:
        return NullCacheStore()

    try:
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
    except Exception:
        return NullCacheStore()
    return RedisCacheStore(client, prefix=prefix)
