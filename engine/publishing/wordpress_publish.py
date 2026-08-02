from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .wordpress_client import WordPressClient
from .wordpress_models import (
    PublishMode,
    WordPressPostRequest,
    WordPressPostResult,
    WordPressResponseError,
)


def wordpress_status(mode: PublishMode) -> str:
    mapping = {
        PublishMode.DRAFT: "draft",
        PublishMode.PUBLISH_NOW: "publish",
        PublishMode.SCHEDULE: "future",
    }
    return mapping[mode]


def validate_schedule(
    mode: PublishMode,
    scheduled_at: datetime | None,
) -> None:
    if mode is not PublishMode.SCHEDULE:
        return

    if scheduled_at is None:
        raise ValueError(
            "Scheduled publication requires scheduled_at."
        )

    value = scheduled_at

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    if value.astimezone(timezone.utc) <= datetime.now(
        timezone.utc
    ):
        raise ValueError(
            "scheduled_at must be in the future."
        )


def parse_post_result(
    payload: dict[str, Any],
) -> WordPressPostResult:
    post_id = payload.get("id")
    status = payload.get("status")
    slug = payload.get("slug")
    link = payload.get("link")

    if not isinstance(post_id, int):
        raise WordPressResponseError(
            "WordPress post response is missing integer id."
        )

    if not isinstance(status, str):
        raise WordPressResponseError(
            "WordPress post response is missing status."
        )

    if not isinstance(slug, str):
        raise WordPressResponseError(
            "WordPress post response is missing slug."
        )

    if link is not None and not isinstance(link, str):
        raise WordPressResponseError(
            "WordPress post link must be a string or null."
        )

    return WordPressPostResult(
        post_id=post_id,
        status=status,
        slug=slug,
        link=link,
        raw=payload,
    )


class WordPressPublisher:
    def __init__(self, client: WordPressClient) -> None:
        self.client = client

    def create(
        self,
        request: WordPressPostRequest,
        mode: PublishMode,
    ) -> WordPressPostResult:
        validate_schedule(mode, request.scheduled_at)

        payload = request.to_payload()
        payload["status"] = wordpress_status(mode)

        response = self.client.create_post(payload)
        return parse_post_result(response)

    def update(
        self,
        post_id: int,
        request: WordPressPostRequest,
        mode: PublishMode,
    ) -> WordPressPostResult:
        validate_schedule(mode, request.scheduled_at)

        payload = request.to_payload()
        payload["status"] = wordpress_status(mode)

        response = self.client.update_post(
            post_id,
            payload,
        )
        return parse_post_result(response)
