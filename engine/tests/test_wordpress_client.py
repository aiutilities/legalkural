from __future__ import annotations

import json
from typing import Any

import pytest

from publishing.wordpress_client import (
    HttpResponse,
    WordPressClient,
)
from publishing.wordpress_models import (
    WordPressConfig,
    WordPressResponseError,
    WordPressTransportError,
)


def config(**overrides: Any) -> WordPressConfig:
    values: dict[str, Any] = {
        "site_url": "https://example.com",
        "username": "admin",
        "application_password": "secret",
        "max_attempts": 3,
        "retry_delay_seconds": 0,
    }
    values.update(overrides)
    return WordPressConfig(**values)


def test_api_url() -> None:
    client = WordPressClient(
        config(site_url="https://example.com/"),
        transport=lambda *_: HttpResponse(
            200,
            {},
            b"{}",
        ),
    )

    assert client.api_url("/wp/v2/posts") == (
        "https://example.com/wp-json/wp/v2/posts"
    )


def test_health_returns_object() -> None:
    def transport(*_: Any) -> HttpResponse:
        return HttpResponse(
            200,
            {},
            json.dumps({"name": "Example"}).encode(),
        )

    client = WordPressClient(
        config(),
        transport=transport,
    )

    assert client.health()["name"] == "Example"


def test_retry_transient_failure() -> None:
    calls = 0

    def transport(*_: Any) -> HttpResponse:
        nonlocal calls
        calls += 1

        if calls < 3:
            return HttpResponse(503, {}, b"{}")

        return HttpResponse(
            200,
            {},
            b'{"ok": true}',
        )

    client = WordPressClient(
        config(),
        transport=transport,
        sleep=lambda _: None,
    )

    assert client.request(
        "GET",
        "wp/v2/posts",
    ) == {"ok": True}
    assert calls == 3


def test_non_json_response_rejected() -> None:
    client = WordPressClient(
        config(),
        transport=lambda *_: HttpResponse(
            200,
            {},
            b"not-json",
        ),
    )

    with pytest.raises(
        WordPressResponseError,
        match="invalid JSON",
    ):
        client.health()


def test_failure_after_max_attempts() -> None:
    client = WordPressClient(
        config(max_attempts=2),
        transport=lambda *_: HttpResponse(
            503,
            {},
            b"{}",
        ),
        sleep=lambda _: None,
    )

    with pytest.raises(
        WordPressTransportError,
        match="2 attempt",
    ):
        client.request(
            "GET",
            "wp/v2/posts",
        )
