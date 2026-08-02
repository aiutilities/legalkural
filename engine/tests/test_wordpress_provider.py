import pytest

from publishing.wordpress_provider import (
    WordPressProvider,
    detect_provider,
)


def test_detect_wordpress_com_subdomain() -> None:
    assert detect_provider(
        "https://yamunaanand.wordpress.com"
    ) is WordPressProvider.WORDPRESS_COM


def test_custom_domain_defaults_to_wordpress_org() -> None:
    assert detect_provider(
        "https://anandnataraj.com"
    ) is WordPressProvider.WORDPRESS_ORG


def test_explicit_wordpress_com_override() -> None:
    assert detect_provider(
        "https://anandnataraj.com",
        "wordpress_com",
    ) is WordPressProvider.WORDPRESS_COM


def test_invalid_provider_rejected() -> None:
    with pytest.raises(ValueError):
        detect_provider(
            "https://example.com",
            "invalid",
        )
