from __future__ import annotations

import mimetypes
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .wordpress_auth import build_auth_headers
from .wordpress_client import HttpResponse
from .wordpress_models import (
    WordPressConfig,
    WordPressResponseError,
    WordPressTransportError,
)


BinaryTransport = Callable[
    [urllib.request.Request, float],
    HttpResponse,
]


def default_binary_transport(
    request: urllib.request.Request,
    timeout: float,
) -> HttpResponse:
    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        return HttpResponse(
            status=int(response.status),
            headers=dict(response.headers.items()),
            body=response.read(),
        )


@dataclass(frozen=True)
class MediaUploadResult:
    media_id: int
    source_url: str | None
    raw: dict[str, Any]


class WordPressMediaUploader:
    def __init__(
        self,
        config: WordPressConfig,
        *,
        transport: BinaryTransport | None = None,
    ) -> None:
        self.config = config
        self.transport = transport or default_binary_transport

    def upload(
        self,
        path: Path,
        *,
        title: str,
        caption: str = "",
        alt_text: str = "",
        description: str = "",
    ) -> MediaUploadResult:
        source = path.expanduser().resolve()

        if not source.exists() or not source.is_file():
            raise FileNotFoundError(source)

        mime_type = (
            mimetypes.guess_type(source.name)[0]
            or "application/octet-stream"
        )

        headers = dict(build_auth_headers(self.config))
        headers.update(
            {
                "Content-Type": mime_type,
                "Content-Disposition": (
                    f'attachment; filename="{source.name}"'
                ),
            }
        )

        request = urllib.request.Request(
            url=(
                f"{self.config.normalized_site_url()}"
                "/wp-json/wp/v2/media"
            ),
            data=source.read_bytes(),
            headers=headers,
            method="POST",
        )

        response = self.transport(
            request,
            self.config.timeout_seconds,
        )

        if not 200 <= response.status < 300:
            raise WordPressTransportError(
                f"Media upload returned HTTP {response.status}."
            )

        import json

        try:
            payload = json.loads(
                response.body.decode("utf-8")
            )
        except Exception as exc:
            raise WordPressResponseError(
                "Media upload returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise WordPressResponseError(
                "Media upload response must be an object."
            )

        media_id = payload.get("id")

        if not isinstance(media_id, int):
            raise WordPressResponseError(
                "Media upload response is missing integer id."
            )

        if any([title, caption, alt_text, description]):
            metadata = {
                "title": title,
                "caption": caption,
                "alt_text": alt_text,
                "description": description,
            }

            metadata_request = urllib.request.Request(
                url=(
                    f"{self.config.normalized_site_url()}"
                    f"/wp-json/wp/v2/media/{media_id}"
                ),
                data=json.dumps(metadata).encode("utf-8"),
                headers={
                    **headers,
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            metadata_response = self.transport(
                metadata_request,
                self.config.timeout_seconds,
            )

            if not 200 <= metadata_response.status < 300:
                raise WordPressTransportError(
                    "Media metadata update failed with HTTP "
                    f"{metadata_response.status}."
                )

        source_url = payload.get("source_url")

        if source_url is not None and not isinstance(
            source_url,
            str,
        ):
            raise WordPressResponseError(
                "Media source_url must be a string or null."
            )

        return MediaUploadResult(
            media_id=media_id,
            source_url=source_url,
            raw=payload,
        )
