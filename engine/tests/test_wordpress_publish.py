from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from publishing.wordpress_models import (
    ContentType,
    PublishMode,
    WordPressPostRequest,
)
from publishing.wordpress_publish import (
    WordPressPublisher,
    wordpress_status,
)


class FakeClient:
    def __init__(self) -> None:
        self.created: dict | None = None
        self.updated: tuple[int, dict] | None = None

    def create_post(self, payload: dict) -> dict:
        self.created = payload
        return {
            "id": 10,
            "status": payload["status"],
            "slug": payload["slug"],
            "link": "https://example.com/post",
        }

    def update_post(
        self,
        post_id: int,
        payload: dict,
    ) -> dict:
        self.updated = (post_id, payload)
        return {
            "id": post_id,
            "status": payload["status"],
            "slug": payload["slug"],
            "link": "https://example.com/post",
        }


def post_request(
    *,
    scheduled_at: datetime | None = None,
) -> WordPressPostRequest:
    return WordPressPostRequest(
        title="Use Reveals the Truth",
        content="<p>Article</p>",
        excerpt="A concise LegalKural excerpt.",
        slug="use-reveals-the-truth",
        content_type=ContentType.JUDGMENT,
        category_ids=(4,),
        tag_ids=(1, 2, 3, 4, 5),
        author_id=1,
        scheduled_at=scheduled_at,
    )


def test_status_mapping() -> None:
    assert wordpress_status(
        PublishMode.DRAFT
    ) == "draft"
    assert wordpress_status(
        PublishMode.PUBLISH_NOW
    ) == "publish"
    assert wordpress_status(
        PublishMode.SCHEDULE
    ) == "future"


def test_create_draft() -> None:
    client = FakeClient()
    publisher = WordPressPublisher(
        client  # type: ignore[arg-type]
    )

    result = publisher.create(
        post_request(),
        PublishMode.DRAFT,
    )

    assert result.post_id == 10
    assert client.created is not None
    assert client.created["status"] == "draft"
    assert (
        client.created["meta"][
            "legalkural_content_type"
        ]
        == "Judgment"
    )


def test_schedule_requires_future_date() -> None:
    client = FakeClient()
    publisher = WordPressPublisher(
        client  # type: ignore[arg-type]
    )

    with pytest.raises(
        ValueError,
        match="future",
    ):
        publisher.create(
            post_request(
                scheduled_at=(
                    datetime.now(timezone.utc)
                    - timedelta(minutes=1)
                )
            ),
            PublishMode.SCHEDULE,
        )


def test_update_post() -> None:
    client = FakeClient()
    publisher = WordPressPublisher(
        client  # type: ignore[arg-type]
    )

    result = publisher.update(
        42,
        post_request(),
        PublishMode.PUBLISH_NOW,
    )

    assert result.post_id == 42
    assert client.updated is not None
    assert client.updated[0] == 42
    assert client.updated[1]["status"] == "publish"
