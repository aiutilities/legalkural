from __future__ import annotations

import pytest

from publishing.wordpress_category_resolver import (
    CategoryResolutionError,
    WordPressCategoryResolver,
)


class FakeClient:
    def __init__(self, result: list[dict]) -> None:
        self.result = result
        self.calls = 0

    def request(self, *_args, **_kwargs):
        self.calls += 1
        return self.result


def test_resolve_frozen_category() -> None:
    client = FakeClient(
        [{"id": 4, "name": "Property Law"}]
    )
    resolver = WordPressCategoryResolver(client)  # type: ignore[arg-type]

    assert resolver.resolve("Property Law") == 4
    assert resolver.resolve("Property Law") == 4
    assert client.calls == 1


def test_reject_category_outside_master() -> None:
    client = FakeClient([])
    resolver = WordPressCategoryResolver(client)  # type: ignore[arg-type]

    with pytest.raises(
        CategoryResolutionError,
        match="frozen master",
    ):
        resolver.resolve("Invented Category")
