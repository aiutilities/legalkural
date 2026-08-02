from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .wordpress_client import WordPressClient
from .wordpress_models import WordPressResponseError


class IdempotencyError(RuntimeError):
    pass


def publication_fingerprint(
    *,
    slug: str,
    title: str,
    content: str,
    excerpt: str,
) -> str:
    payload = {
        "slug": slug,
        "title": title,
        "content": content,
        "excerpt": excerpt,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class PublicationRegistry:
    path: Path

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "schema_version": "1.0",
                "publications": {},
            }

        return json.loads(
            self.path.read_text(encoding="utf-8")
        )

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    def get(self, slug: str) -> dict[str, Any] | None:
        return self._read()["publications"].get(slug)

    def record(
        self,
        *,
        slug: str,
        post_id: int,
        fingerprint: str,
    ) -> None:
        payload = self._read()
        payload["publications"][slug] = {
            "post_id": post_id,
            "fingerprint": fingerprint,
        }
        self._write(payload)


class IdempotentWordPressPublisher:
    def __init__(
        self,
        client: WordPressClient,
        registry: PublicationRegistry,
    ) -> None:
        self.client = client
        self.registry = registry

    def existing_post_id(self, slug: str) -> int | None:
        local = self.registry.get(slug)

        if local:
            post_id = local.get("post_id")
            if isinstance(post_id, int):
                return post_id

        result = self.client.request(
            "GET",
            "wp/v2/posts",
            query={
                "slug": slug,
                "context": "edit",
                "status": "any",
                "per_page": 100,
            },
        )

        if not isinstance(result, list):
            raise WordPressResponseError(
                "Slug lookup response must be a list."
            )

        if len(result) > 1:
            raise IdempotencyError(
                f"Multiple WordPress posts found for slug: {slug}"
            )

        if not result:
            return None

        post_id = result[0].get("id")

        if not isinstance(post_id, int):
            raise WordPressResponseError(
                "Slug lookup result is missing integer id."
            )

        return post_id

    def create_or_update(
        self,
        *,
        slug: str,
        payload: dict[str, Any],
        fingerprint: str,
    ) -> tuple[str, dict[str, Any]]:
        post_id = self.existing_post_id(slug)

        if post_id is None:
            response = self.client.create_post(payload)
            action = "CREATED"
        else:
            response = self.client.update_post(
                post_id,
                payload,
            )
            action = "UPDATED"

        resolved_id = response.get("id")

        if not isinstance(resolved_id, int):
            raise WordPressResponseError(
                "Publication response is missing integer id."
            )

        self.registry.record(
            slug=slug,
            post_id=resolved_id,
            fingerprint=fingerprint,
        )

        return action, response
