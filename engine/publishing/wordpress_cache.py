from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


@dataclass
class MemoryCache(Generic[T]):
    ttl_seconds: float = 300.0
    _values: dict[str, CacheEntry[T]] = field(
        default_factory=dict
    )

    def get(self, key: str) -> T | None:
        entry = self._values.get(key)

        if entry is None:
            return None

        if entry.expires_at <= monotonic():
            self._values.pop(key, None)
            return None

        return entry.value

    def set(self, key: str, value: T) -> None:
        self._values[key] = CacheEntry(
            value=value,
            expires_at=monotonic() + self.ttl_seconds,
        )

    def clear(self) -> None:
        self._values.clear()
