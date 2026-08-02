from __future__ import annotations

import base64

import pytest

from publishing.wordpress_auth import (
    build_auth_headers,
    validate_config,
)
from publishing.wordpress_models import (
    WordPressConfig,
    WordPressConfigurationError,
)


def valid_config() -> WordPressConfig:
    return WordPressConfig(
        site_url="https://example.com",
        username="admin",
        application_password="abcd efgh",
    )


def test_build_auth_headers() -> None:
    headers = build_auth_headers(valid_config())
    expected = base64.b64encode(
        b"admin:abcd efgh"
    ).decode("ascii")

    assert headers["Authorization"] == f"Basic {expected}"
    assert headers["Accept"] == "application/json"


def test_reject_missing_site_url() -> None:
    value = valid_config()
    invalid = WordPressConfig(
        site_url="",
        username=value.username,
        application_password=value.application_password,
    )

    with pytest.raises(
        WordPressConfigurationError,
        match="site_url",
    ):
        validate_config(invalid)


def test_reject_invalid_attempt_count() -> None:
    value = valid_config()
    invalid = WordPressConfig(
        site_url=value.site_url,
        username=value.username,
        application_password=value.application_password,
        max_attempts=0,
    )

    with pytest.raises(
        WordPressConfigurationError,
        match="max_attempts",
    ):
        validate_config(invalid)
