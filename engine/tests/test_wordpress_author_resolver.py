from __future__ import annotations

import pytest

from publishing.wordpress_author_resolver import (
    AuthorResolutionError,
    WordPressAuthorResolver,
)


class FakeClient:
    def current_user(self):
        return {"id": 1, "name": "Admin"}

    def request(self, *_args, **kwargs):
        name = kwargs["query"]["search"]
        if name == "Volunteer Editor":
            return [{"id": 9, "name": "Volunteer Editor"}]
        return []


def test_admin_resolves_current_user() -> None:
    resolver = WordPressAuthorResolver(
        FakeClient()  # type: ignore[arg-type]
    )
    assert resolver.resolve() == 1


def test_resolve_volunteer_editor() -> None:
    resolver = WordPressAuthorResolver(
        FakeClient()  # type: ignore[arg-type]
    )
    assert resolver.resolve("Volunteer Editor") == 9


def test_missing_author_fails() -> None:
    resolver = WordPressAuthorResolver(
        FakeClient()  # type: ignore[arg-type]
    )

    with pytest.raises(
        AuthorResolutionError,
        match="exactly one",
    ):
        resolver.resolve("Unknown")
