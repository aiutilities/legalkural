import json
from typing import Any

import pytest

from publishing.wordpress_com_auth import (
    WordPressComConfig,
)
from publishing.wordpress_com_client import (
    WordPressComClient,
    WordPressComHttpResponse,
)
from publishing.wordpress_models import (
    WordPressResponseError,
)


SITE = "lkaidpl.wordpress.com"
SITE_ROUTE = f"/wp/v2/sites/{SITE}"


def config() -> WordPressComConfig:
    return WordPressComConfig(
        site_identifier=SITE,
        access_token="token",
        retry_delay_seconds=0,
    )


def response(payload: Any) -> WordPressComHttpResponse:
    return WordPressComHttpResponse(
        200,
        {},
        json.dumps(payload).encode("utf-8"),
    )


def test_site_summary_is_concise() -> None:
    payload = {
        "namespace": "wp/v2",
        "routes": {
            SITE_ROUTE: {
                "methods": ["GET"],
            },
            f"{SITE_ROUTE}/posts": {
                "methods": ["GET", "POST"],
            },
            f"{SITE_ROUTE}/categories": {
                "methods": ["GET", "POST"],
            },
            f"{SITE_ROUTE}/tags": {
                "methods": ["GET", "POST"],
            },
            f"{SITE_ROUTE}/media": {
                "methods": ["GET", "POST"],
            },
        },
    }

    client = WordPressComClient(
        config(),
        transport=lambda *_: response(payload),
    )

    result = client.site_summary()

    assert result["status"] == "CONNECTED"
    assert result["site_identifier"] == SITE
    assert result["site_route"] == SITE_ROUTE
    assert result["capabilities"] == {
        "posts": True,
        "categories": True,
        "tags": True,
        "media": True,
    }
    assert "routes" not in result


def test_site_summary_requires_site_route() -> None:
    client = WordPressComClient(
        config(),
        transport=lambda *_: response(
            {
                "namespace": "wp/v2",
                "routes": {},
            }
        ),
    )

    with pytest.raises(
        WordPressResponseError,
        match="site route",
    ):
        client.site_summary()
