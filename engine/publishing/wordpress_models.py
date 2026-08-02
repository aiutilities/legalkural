from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class WordPressError(RuntimeError):
    """Base error for WordPress publishing."""


class WordPressConfigurationError(WordPressError):
    """Raised when configuration is invalid."""


class WordPressTransportError(WordPressError):
    """Raised for network or HTTP failures."""


class WordPressResponseError(WordPressError):
    """Raised when WordPress returns an invalid response."""


class ContentType(str, Enum):
    JUDGMENT = "Judgment"
    NEWS = "News"
    COLUMN = "Column"
    INTERVIEW = "Interview"


class PublishMode(str, Enum):
    DRAFT = "DRAFT"
    PUBLISH_NOW = "PUBLISH_NOW"
    SCHEDULE = "SCHEDULE"


@dataclass(frozen=True)
class WordPressConfig:
    site_url: str
    username: str
    application_password: str
    verify_ssl: bool = True
    timeout_seconds: float = 30.0
    max_attempts: int = 3
    retry_delay_seconds: float = 1.0
    user_agent: str = "LegalKural/1.0"

    def normalized_site_url(self) -> str:
        return self.site_url.rstrip("/")


@dataclass(frozen=True)
class WordPressPostRequest:
    title: str
    content: str
    excerpt: str
    slug: str
    content_type: ContentType
    category_ids: tuple[int, ...] = ()
    tag_ids: tuple[int, ...] = ()
    author_id: int | None = None
    featured_media_id: int | None = None
    scheduled_at: datetime | None = None
    meta: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": self.title,
            "content": self.content,
            "excerpt": self.excerpt,
            "slug": self.slug,
            "categories": list(self.category_ids),
            "tags": list(self.tag_ids),
            "meta": {
                "legalkural_content_type": self.content_type.value,
                **(self.meta or {}),
            },
        }

        if self.author_id is not None:
            payload["author"] = self.author_id

        if self.featured_media_id is not None:
            payload["featured_media"] = self.featured_media_id

        if self.scheduled_at is not None:
            payload["date"] = self.scheduled_at.isoformat()

        return payload


@dataclass(frozen=True)
class WordPressPostResult:
    post_id: int
    status: str
    slug: str
    link: str | None
    raw: dict[str, Any]
