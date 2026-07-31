import socket
from unittest.mock import patch

import pytest

from aidpl.providers.http import ProviderHTTPError, post_json


class FakeResponse:
    def __init__(self) -> None:
        self.headers = {"x-request-id": "req-test"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return b'{"status":"ok"}'


def test_post_json_retries_timeout() -> None:
    effects = [
        socket.timeout("slow"),
        FakeResponse(),
    ]

    with patch(
        "urllib.request.urlopen",
        side_effect=effects,
    ) as mocked:
        payload, headers = post_json(
            url="https://example.invalid",
            headers={},
            payload={"test": True},
            timeout_seconds=1,
            max_attempts=2,
            retry_delay_seconds=0,
        )

    assert mocked.call_count == 2
    assert payload["status"] == "ok"
    assert headers["x-request-id"] == "req-test"


def test_post_json_fails_after_retries() -> None:
    with patch(
        "urllib.request.urlopen",
        side_effect=socket.timeout("slow"),
    ):
        with pytest.raises(
            ProviderHTTPError,
            match="after 2 attempts",
        ):
            post_json(
                url="https://example.invalid",
                headers={},
                payload={"test": True},
                timeout_seconds=1,
                max_attempts=2,
                retry_delay_seconds=0,
            )
