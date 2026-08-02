from __future__ import annotations

from .wordpress_cache import MemoryCache
from .wordpress_client import WordPressClient
from .wordpress_models import WordPressResponseError


class AuthorResolutionError(ValueError):
    pass


class WordPressAuthorResolver:
    def __init__(
        self,
        client: WordPressClient,
        *,
        cache: MemoryCache[int] | None = None,
    ) -> None:
        self.client = client
        self.cache = cache or MemoryCache()

    def resolve(self, display_name: str = "admin") -> int:
        cache_key = display_name.casefold()
        cached = self.cache.get(cache_key)

        if cached is not None:
            return cached

        if cache_key == "admin":
            user = self.client.current_user()
            user_id = user.get("id")

            if not isinstance(user_id, int):
                raise WordPressResponseError(
                    "Current user is missing integer id."
                )

            self.cache.set(cache_key, user_id)
            return user_id

        result = self.client.request(
            "GET",
            "wp/v2/users",
            query={
                "search": display_name,
                "context": "edit",
                "per_page": 100,
            },
        )

        if not isinstance(result, list):
            raise WordPressResponseError(
                "Author search response must be a list."
            )

        exact = [
            item
            for item in result
            if isinstance(item, dict)
            and str(item.get("name", "")).casefold()
            == display_name.casefold()
        ]

        if len(exact) != 1:
            raise AuthorResolutionError(
                f"Expected exactly one active author named "
                f"'{display_name}', found {len(exact)}."
            )

        user_id = exact[0].get("id")

        if not isinstance(user_id, int):
            raise WordPressResponseError(
                "Resolved author is missing integer id."
            )

        self.cache.set(cache_key, user_id)
        return user_id
