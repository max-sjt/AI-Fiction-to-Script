from __future__ import annotations

from collections.abc import Iterable


def make_id(prefix: str, index: int, width: int = 3) -> str:
    if prefix == "a":
        return f"{prefix}{index}"
    return f"{prefix}{index:0{width}d}"


def next_available_id(prefix: str, existing_ids: Iterable[str], width: int = 3) -> str:
    existing = set(existing_ids)
    index = 1
    while True:
        candidate = make_id(prefix, index, width=width)
        if candidate not in existing:
            return candidate
        index += 1

