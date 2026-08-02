import pytest

from publishing.wordpress_com_auth import (
    WordPressComConfig,
    WordPressComConfigurationError,
    build_headers,
)


def config() -> WordPressComConfig:
    return WordPressComConfig(
        site_identifier="anandnataraj.com",
        access_token="token-value",
    )


def test_api_base_url() -> None:
    assert config().api_base_url() == (
        "https://public-api.wordpress.com"
        "/wp/v2/sites/anandnataraj.com"
    )


def test_bearer_header() -> None:
    headers = build_headers(config())
    assert headers["Authorization"] == (
        "Bearer token-value"
    )


def test_token_required() -> None:
    with pytest.raises(
        WordPressComConfigurationError,
        match="access_token",
    ):
        build_headers(
            WordPressComConfig(
                site_identifier="anandnataraj.com",
                access_token="",
            )
        )
