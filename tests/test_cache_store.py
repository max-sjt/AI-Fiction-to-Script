from __future__ import annotations

from ai_fiction_to_script.services.cache_store import InMemoryCacheStore


def test_in_memory_cache_store_roundtrip_and_prefix_delete() -> None:
    cache = InMemoryCacheStore()

    cache.set_json("projects", {"items": [1]}, ttl_seconds=60)
    cache.set_json("projects:web-demo:versions", {"items": [2]}, ttl_seconds=60)
    cache.set_json("other", {"items": [3]}, ttl_seconds=60)

    assert cache.get_json("projects") == {"items": [1]}
    assert cache.get_json("projects:web-demo:versions") == {"items": [2]}

    cache.delete_prefix("projects")

    assert cache.get_json("projects") is None
    assert cache.get_json("projects:web-demo:versions") is None
    assert cache.get_json("other") == {"items": [3]}
