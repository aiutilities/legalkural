from __future__ import annotations

import base64
from typing import Mapping

from .wordpress_models import (
    WordPressConfig,
    WordPressConfigurationError,
)


def validate_config(config: WordPressConfig) -> None:
    if not config.site_url.strip():
        raise WordPressConfigurationError("site_url is required.")

    if not (
        config.site_url.startswith("https://")
        or config.site_url.startswith("http://")
    ):
        raise WordPressConfigurationError(
            "site_url must use HTTP or HTTPS."
        )

    if not config.username.strip():
        raise WordPressConfigurationError("username is required.")

    if not config.application_password.strip():
        raise WordPressConfigurationError(
            "application_password is required."
        )

    if config.timeout_seconds <= 0:
        raise WordPressConfigurationError(
            "timeout_seconds must be greater than zero."
        )

    if config.max_attempts < 1:
        raise WordPressConfigurationError(
            "max_attempts must be at least one."
        )

    if config.retry_delay_seconds < 0:
        raise WordPressConfigurationError(
            "retry_delay_seconds cannot be negative."
        )


def build_auth_headers(
    config: WordPressConfig,
) -> Mapping[str, str]:
    validate_config(config)

    credentials = (
        f"{config.username}:{config.application_password}"
    ).encode("utf-8")
    token = base64.b64encode(credentials).decode("ascii")

    return {
        "Authorization": f"Basic {token}",
        "Accept": "application/json",
        "User-Agent": config.user_agent,
    }
