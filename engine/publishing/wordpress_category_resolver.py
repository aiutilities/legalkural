from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .wordpress_cache import MemoryCache
from .wordpress_client import WordPressClient
from .wordpress_models import WordPressResponseError


ROOT = Path(__file__).resolve().parents[2]
CATEGORY_MASTER = (
    ROOT / "engine" / "config" / "wordpress_categories.json"
)


class CategoryResolutionError(ValueError):
    pass


def frozen_categories() -> list[str]:
    payload = json.loads(
        CATEGORY_MASTER.read_text(encoding="utf-8")
    )

    if payload.get("status") != "FROZEN":
        raise CategoryResolutionError(
            "WordPress category master is not frozen."
        )

    values = payload.get("categories")

    if not isinstance(values, list) or not values:
        raise CategoryResolutionError(
            "WordPress category master is empty."
        )

    return [str(item) for item in values]


class WordPressCategoryResolver:
    def __init__(
        self,
        client: WordPressClient,
        *,
        cache: MemoryCache[int] | None = None,
    ) -> None:
        self.client = client
        self.cache = cache or MemoryCache()

    def resolve(self, category_name: str) -> int:
        if category_name not in frozen_categories():
            raise CategoryResolutionError(
                "Category must come from the frozen master."
            )

        cache_key = category_name.casefold()
        cached = self.cache.get(cache_key)

        if cached is not None:
            return cached

        result = self.client.request(
            "GET",
            "wp/v2/categories",
            query={
                "search": category_name,
                "per_page": 100,
            },
        )

        if not isinstance(result, list):
            raise WordPressResponseError(
                "Category search response must be a list."
            )

        exact = [
            item
            for item in result
            if isinstance(item, dict)
            and str(item.get("name", "")).casefold()
            == category_name.casefold()
        ]

        if len(exact) != 1:
            raise CategoryResolutionError(
                f"Expected exactly one WordPress category "
                f"named '{category_name}', found {len(exact)}."
            )

        category_id = exact[0].get("id")

        if not isinstance(category_id, int):
            raise WordPressResponseError(
                "Resolved category is missing integer id."
            )

        self.cache.set(cache_key, category_id)
        return category_id
