from __future__ import annotations

import re

from .wordpress_cache import MemoryCache
from .wordpress_client import WordPressClient
from .wordpress_models import WordPressResponseError


class TagResolutionError(ValueError):
    pass


def normalize_tags(tags: list[str]) -> list[str]:
    if not 5 <= len(tags) <= 9:
        raise TagResolutionError(
            "Tags must contain between 5 and 9 entries."
        )

    normalized: list[str] = []
    seen: set[str] = set()

    for raw in tags:
        value = raw.strip()

        if not value:
            raise TagResolutionError(
                "Empty tags are not allowed."
            )

        if re.search(r"\s", value):
            raise TagResolutionError(
                f"Tag must be a single word: {value}"
            )

        key = value.casefold()

        if key in seen:
            continue

        seen.add(key)
        normalized.append(value)

    if not 5 <= len(normalized) <= 9:
        raise TagResolutionError(
            "Tags must contain 5 to 9 unique entries."
        )

    return sorted(normalized, key=str.casefold)


class WordPressTagResolver:
    def __init__(
        self,
        client: WordPressClient,
        *,
        auto_create: bool = True,
        cache: MemoryCache[int] | None = None,
    ) -> None:
        self.client = client
        self.auto_create = auto_create
        self.cache = cache or MemoryCache()

    def resolve_many(self, tags: list[str]) -> list[int]:
        return [self.resolve(tag) for tag in normalize_tags(tags)]

    def resolve(self, tag_name: str) -> int:
        cache_key = tag_name.casefold()
        cached = self.cache.get(cache_key)

        if cached is not None:
            return cached

        result = self.client.request(
            "GET",
            "wp/v2/tags",
            query={
                "search": tag_name,
                "per_page": 100,
            },
        )

        if not isinstance(result, list):
            raise WordPressResponseError(
                "Tag search response must be a list."
            )

        for item in result:
            if (
                isinstance(item, dict)
                and str(item.get("name", "")).casefold()
                == tag_name.casefold()
            ):
                tag_id = item.get("id")

                if not isinstance(tag_id, int):
                    raise WordPressResponseError(
                        "Resolved tag is missing integer id."
                    )

                self.cache.set(cache_key, tag_id)
                return tag_id

        if not self.auto_create:
            raise TagResolutionError(
                f"WordPress tag does not exist: {tag_name}"
            )

        created = self.client.request(
            "POST",
            "wp/v2/tags",
            payload={"name": tag_name},
        )

        if not isinstance(created, dict):
            raise WordPressResponseError(
                "Create-tag response must be an object."
            )

        tag_id = created.get("id")

        if not isinstance(tag_id, int):
            raise WordPressResponseError(
                "Created tag is missing integer id."
            )

        self.cache.set(cache_key, tag_id)
        return tag_id
