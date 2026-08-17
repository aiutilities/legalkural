from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .wordpress_com_auth import (
    WordPressComConfig,
    build_headers,
    validate_config,
)
from .wordpress_models import (
    WordPressResponseError,
    WordPressTransportError,
)


TRANSIENT_HTTP_CODES = {
    408,
    425,
    429,
    500,
    502,
    503,
    504,
    520,
}


@dataclass(frozen=True)
class WordPressComHttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


Transport = Callable[
    [urllib.request.Request, float],
    WordPressComHttpResponse,
]


def default_transport(
    request: urllib.request.Request,
    timeout: float,
) -> WordPressComHttpResponse:
    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        return WordPressComHttpResponse(
            status=int(response.status),
            headers=dict(response.headers.items()),
            body=response.read(),
        )


class WordPressComClient:
    def __init__(
        self,
        config: WordPressComConfig,
        *,
        transport: Transport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        validate_config(config)
        self.config = config
        self.transport = transport or default_transport
        self.sleep = sleep

    def api_url(self, path: str) -> str:
        clean = path.lstrip("/")
        base = self.config.api_base_url()

        if not clean:
            return base

        return f"{base}/{clean}"

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> Any:
        url = self.api_url(path)

        if query:
            url = (
                f"{url}?"
                f"{urllib.parse.urlencode(query, doseq=True)}"
            )

        body: bytes | None = None
        headers = dict(build_headers(self.config))

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        if extra_headers:
            headers.update(extra_headers)

        request = urllib.request.Request(
            url=url,
            data=body,
            headers=headers,
            method=method.upper(),
        )

        last_error: Exception | None = None

        for attempt in range(
            1,
            self.config.max_attempts + 1,
        ):
            try:
                response = self.transport(
                    request,
                    self.config.timeout_seconds,
                )

                if response.status in TRANSIENT_HTTP_CODES:
                    raise WordPressTransportError(
                        "Transient WordPress.com HTTP "
                        f"{response.status}."
                    )

                if not 200 <= response.status < 300:
                    raise WordPressTransportError(
                        "WordPress.com returned HTTP "
                        f"{response.status}."
                    )

                if not response.body:
                    return None

                try:
                    return json.loads(
                        response.body.decode("utf-8")
                    )
                except (
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                ) as exc:
                    raise WordPressResponseError(
                        "WordPress.com returned invalid JSON."
                    ) from exc

            except urllib.error.HTTPError as exc:
                message = exc.read().decode(
                    "utf-8",
                    errors="replace",
                )
                last_error = WordPressTransportError(
                    f"WordPress.com HTTP {exc.code}: {message}"
                )

                if exc.code not in TRANSIENT_HTTP_CODES:
                    raise last_error from exc

            except (
                urllib.error.URLError,
                socket.timeout,
                TimeoutError,
                ConnectionError,
                WordPressTransportError,
            ) as exc:
                last_error = exc

            if attempt < self.config.max_attempts:
                self.sleep(
                    self.config.retry_delay_seconds * attempt
                )

        raise WordPressTransportError(
            "WordPress.com request failed after "
            f"{self.config.max_attempts} attempt(s): "
            f"{last_error}"
        ) from last_error

    def current_user(self) -> dict[str, Any]:
        result = self.request(
            "GET",
            "users/me",
            query={"context": "edit"},
        )

        if not isinstance(result, dict):
            raise WordPressResponseError(
                "WordPress.com current-user response must be an object."
            )

        user_id = result.get("id")

        if not isinstance(user_id, int):
            raise WordPressResponseError(
                "WordPress.com current-user response is missing integer id."
            )

        return result

    def site(self) -> dict[str, Any]:
        result = self.request("GET", "")

        if not isinstance(result, dict):
            raise WordPressResponseError(
                "WordPress.com site response must be an object."
            )

        return result

    def site_summary(self) -> dict[str, Any]:
        # Return concise WordPress.com site connectivity details.
        index = self.site()
        routes = index.get("routes")

        if not isinstance(routes, dict):
            raise WordPressResponseError(
                "WordPress.com site index is missing routes."
            )

        site_route = (
            f"/wp/v2/sites/{self.config.site_identifier}"
        )
        route = routes.get(site_route)

        if not isinstance(route, dict):
            raise WordPressResponseError(
                "Configured WordPress.com site route was not "
                f"found: {site_route}"
            )

        methods = route.get("methods", [])
        if not isinstance(methods, list):
            methods = []

        return {
            "status": "CONNECTED",
            "provider": "wordpress_com",
            "site_identifier": (
                self.config.site_identifier
            ),
            "api_base_url": (
                self.config.api_base_url()
            ),
            "site_route": site_route,
            "site_methods": methods,
            "capabilities": {
                "posts": (
                    f"{site_route}/posts" in routes
                ),
                "categories": (
                    f"{site_route}/categories" in routes
                ),
                "tags": (
                    f"{site_route}/tags" in routes
                ),
                "media": (
                    f"{site_route}/media" in routes
                ),
            },
            "route_count": len(routes),
        }

    def posts(
        self,
        **query: Any,
    ) -> list[dict[str, Any]]:
        result = self.request(
            "GET",
            "posts",
            query=query or None,
        )

        if not isinstance(result, list):
            raise WordPressResponseError(
                "WordPress.com posts response must be a list."
            )

        return result

    def create_post(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        result = self.request(
            "POST",
            "posts",
            payload=payload,
        )

        if not isinstance(result, dict):
            raise WordPressResponseError(
                "Create-post response must be an object."
            )

        return result

    def update_post(
        self,
        post_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if post_id <= 0:
            raise ValueError(
                "post_id must be positive."
            )

        result = self.request(
            "POST",
            f"posts/{post_id}",
            payload=payload,
        )

        if not isinstance(result, dict):
            raise WordPressResponseError(
                "Update-post response must be an object."
            )

        return result

    def categories(
        self,
        **query: Any,
    ) -> list[dict[str, Any]]:
        result = self.request(
            "GET",
            "categories",
            query=query or None,
        )

        if not isinstance(result, list):
            raise WordPressResponseError(
                "Categories response must be a list."
            )

        return result

    def tags(
        self,
        **query: Any,
    ) -> list[dict[str, Any]]:
        result = self.request(
            "GET",
            "tags",
            query=query or None,
        )

        if not isinstance(result, list):
            raise WordPressResponseError(
                "Tags response must be a list."
            )

        return result
