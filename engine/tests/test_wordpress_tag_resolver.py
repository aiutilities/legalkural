from __future__ import annotations

import pytest

from publishing.wordpress_tag_resolver import (
    TagResolutionError,
    WordPressTagResolver,
    normalize_tags,
)


class FakeClient:
    def __init__(self) -> None:
        self.created = 0

    def request(self, method, path, **kwargs):
        if method == "GET":
            tag = kwargs["query"]["search"]
            if tag == "taxation":
                return [{"id": 7, "name": "taxation"}]
            return []

        self.created += 1
        return {
            "id": 100 + self.created,
            "name": kwargs["payload"]["name"],
        }


def test_normalize_tags() -> None:
    result = normalize_tags(
        [
            "Taxation",
            "property",
            "Court",
            "Appeal",
            "Housing",
        ]
    )

    assert result == [
        "Appeal",
        "Court",
        "Housing",
        "property",
        "Taxation",
    ]


def test_reject_multiword_tag() -> None:
    with pytest.raises(
        TagResolutionError,
        match="single word",
    ):
        normalize_tags(
            [
                "property law",
                "court",
                "appeal",
                "housing",
                "taxation",
            ]
        )


def test_resolve_existing_and_create_missing() -> None:
    client = FakeClient()
    resolver = WordPressTagResolver(client)  # type: ignore[arg-type]

    ids = resolver.resolve_many(
        [
            "taxation",
            "property",
            "court",
            "appeal",
            "housing",
        ]
    )

    assert 7 in ids
    assert len(ids) == 5
    assert client.created == 4
