import json
from typing import Any

from publishing.wordpress_com_auth import (
    WordPressComConfig,
)
from publishing.wordpress_com_client import (
    WordPressComClient,
    WordPressComHttpResponse,
)


def config() -> WordPressComConfig:
    return WordPressComConfig(
        site_identifier="56733028",
        access_token="token",
        retry_delay_seconds=0,
    )


def test_api_url_uses_public_proxy() -> None:
    client = WordPressComClient(
        config(),
        transport=lambda *_: WordPressComHttpResponse(
            200,
            {},
            b"{}",
        ),
    )

    assert client.api_url("posts") == (
        "https://public-api.wordpress.com"
        "/wp/v2/sites/56733028/posts"
    )


def test_site_response() -> None:
    def transport(*_: Any) -> WordPressComHttpResponse:
        return WordPressComHttpResponse(
            200,
            {},
            json.dumps(
                {
                    "id": 56733028,
                    "name": "AnandNataraj",
                }
            ).encode(),
        )

    client = WordPressComClient(
        config(),
        transport=transport,
    )

    assert client.site()["id"] == 56733028


def test_create_post() -> None:
    captured = {}

    def transport(
        request,
        _timeout,
    ) -> WordPressComHttpResponse:
        captured["method"] = request.get_method()
        captured["url"] = request.full_url
        captured["auth"] = request.headers.get(
            "Authorization"
        )

        return WordPressComHttpResponse(
            201,
            {},
            b'{"id": 10, "status": "draft"}',
        )

    client = WordPressComClient(
        config(),
        transport=transport,
    )

    result = client.create_post(
        {
            "title": "LegalKural Test",
            "status": "draft",
        }
    )

    assert result["id"] == 10
    assert captured["method"] == "POST"
    assert captured["auth"] == "Bearer token"
