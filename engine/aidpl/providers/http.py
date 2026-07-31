from __future__ import annotations

import json
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
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ProviderHTTPError(
            f"Provider returned HTTP {exc.code}: {body[:1000]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ProviderHTTPError(
            f"Provider request failed: {exc.reason}"
        ) from exc

    try:
        payload_out = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ProviderHTTPError(
            "Provider returned a non-JSON response."
        ) from exc

    return payload_out, response_headers
