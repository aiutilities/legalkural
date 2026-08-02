from __future__ import annotations

from dataclasses import dataclass


class WordPressComConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class WordPressComConfig:
    site_identifier: str
    access_token: str
    timeout_seconds: float = 30.0
    max_attempts: int = 3
    retry_delay_seconds: float = 1.0
    user_agent: str = "LegalKural/1.0"

    def api_base_url(self) -> str:
        identifier = self.site_identifier.strip().strip("/")

        if not identifier:
            raise WordPressComConfigurationError(
                "site_identifier is required."
            )

        return (
            "https://public-api.wordpress.com"
            f"/wp/v2/sites/{identifier}"
        )


def validate_config(config: WordPressComConfig) -> None:
    if not config.site_identifier.strip():
        raise WordPressComConfigurationError(
            "site_identifier is required."
        )

    if not config.access_token.strip():
        raise WordPressComConfigurationError(
            "access_token is required."
        )

    if config.timeout_seconds <= 0:
        raise WordPressComConfigurationError(
            "timeout_seconds must be greater than zero."
        )

    if config.max_attempts < 1:
        raise WordPressComConfigurationError(
            "max_attempts must be at least one."
        )

    if config.retry_delay_seconds < 0:
        raise WordPressComConfigurationError(
            "retry_delay_seconds cannot be negative."
        )


def build_headers(
    config: WordPressComConfig,
) -> dict[str, str]:
    validate_config(config)

    return {
        "Authorization": (
            f"Bearer {config.access_token.strip()}"
        ),
        "Accept": "application/json",
        "User-Agent": config.user_agent,
    }
