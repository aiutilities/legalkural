from __future__ import annotations

from enum import Enum
from urllib.parse import urlparse


class WordPressProvider(str, Enum):
    WORDPRESS_ORG = "wordpress_org"
    WORDPRESS_COM = "wordpress_com"


def detect_provider(
    site_url: str,
    explicit: str | None = None,
) -> WordPressProvider:
    if explicit:
        try:
            return WordPressProvider(explicit)
        except ValueError as exc:
            raise ValueError(
                "WORDPRESS_PROVIDER must be "
                "'wordpress_org' or 'wordpress_com'."
            ) from exc

    host = urlparse(site_url).hostname or ""

    if host.endswith(".wordpress.com"):
        return WordPressProvider.WORDPRESS_COM

    return WordPressProvider.WORDPRESS_ORG
