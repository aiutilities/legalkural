from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any


class ProviderHTTPError(RuntimeError):
    pass


def post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
    max_attempts: int = 3,
    retry_delay_seconds: float = 2.0,
) -> tuple[dict[str, Any], dict[str, str]]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=data,
        headers={
            "Content-Type": "application/json",
            **headers,
        },
        method="POST",
    )

    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout_seconds,
            ) as response:
                body = response.read().decode("utf-8")
                response_headers = {
                    key.lower(): value
                    for key, value in response.headers.items()
                }

            try:
                payload_out = json.loads(body)
            except json.JSONDecodeError as exc:
                raise ProviderHTTPError(
                    "Provider returned a non-JSON response."
                ) from exc

            return payload_out, response_headers

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ProviderHTTPError(
                f"Provider returned HTTP {exc.code}: {body[:1000]}"
            ) from exc

        except (
            TimeoutError,
            socket.timeout,
            urllib.error.URLError,
        ) as exc:
            last_error = exc

            if attempt >= max_attempts:
                break

            time.sleep(retry_delay_seconds * attempt)

    raise ProviderHTTPError(
        "Provider request timed out or failed after "
        f"{max_attempts} attempts: {last_error}"
    )
