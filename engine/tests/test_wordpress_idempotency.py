from __future__ import annotations

from pathlib import Path

from publishing.wordpress_idempotency import (
    IdempotentWordPressPublisher,
    PublicationRegistry,
    publication_fingerprint,
)


class FakeClient:
    def __init__(self, existing: list[dict] | None = None) -> None:
        self.existing = existing or []
        self.created = 0
        self.updated = 0

    def request(self, *_args, **_kwargs):
        return self.existing

    def create_post(self, payload):
        self.created += 1
        return {
            "id": 10,
            "slug": payload["slug"],
            "status": payload["status"],
        }

    def update_post(self, post_id, payload):
        self.updated += 1
        return {
            "id": post_id,
            "slug": payload["slug"],
            "status": payload["status"],
        }


def test_fingerprint_is_stable() -> None:
    one = publication_fingerprint(
        slug="case",
        title="Case",
        content="Body",
        excerpt="Excerpt",
    )
    two = publication_fingerprint(
        slug="case",
        title="Case",
        content="Body",
        excerpt="Excerpt",
    )

    assert one == two
    assert len(one) == 64


def test_create_when_slug_missing(tmp_path: Path) -> None:
    client = FakeClient()
    registry = PublicationRegistry(
        tmp_path / "registry.json"
    )
    publisher = IdempotentWordPressPublisher(
        client,  # type: ignore[arg-type]
        registry,
    )

    action, response = publisher.create_or_update(
        slug="case",
        payload={
            "slug": "case",
            "status": "draft",
        },
        fingerprint="a" * 64,
    )

    assert action == "CREATED"
    assert response["id"] == 10
    assert client.created == 1
    assert registry.get("case")["post_id"] == 10


def test_update_when_slug_exists(tmp_path: Path) -> None:
    client = FakeClient(
        existing=[{"id": 22, "slug": "case"}]
    )
    registry = PublicationRegistry(
        tmp_path / "registry.json"
    )
    publisher = IdempotentWordPressPublisher(
        client,  # type: ignore[arg-type]
        registry,
    )

    action, response = publisher.create_or_update(
        slug="case",
        payload={
            "slug": "case",
            "status": "draft",
        },
        fingerprint="b" * 64,
    )

    assert action == "UPDATED"
    assert response["id"] == 22
    assert client.updated == 1
