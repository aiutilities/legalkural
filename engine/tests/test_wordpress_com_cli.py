import json
import sys

from publishing import wordpress_com_cli


class FakeWordPressComClient:
    def __init__(self, _config) -> None:
        self.current_user_called = False

    def current_user(self) -> dict:
        self.current_user_called = True
        return {
            "id": 42,
            "name": "Existing Author",
            "slug": "existing-author",
        }

    def site_summary(self) -> dict:
        raise AssertionError(
            "whoami must not call site_summary"
        )


def test_whoami_calls_current_user(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        wordpress_com_cli,
        "config_from_environment",
        lambda: object(),
    )
    monkeypatch.setattr(
        wordpress_com_cli,
        "WordPressComClient",
        FakeWordPressComClient,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "legalkural-wordpress-com",
            "whoami",
        ],
    )

    result = wordpress_com_cli.main()

    assert result == 0

    payload = json.loads(
        capsys.readouterr().out
    )

    assert payload["id"] == 42
    assert payload["name"] == "Existing Author"
    assert payload["slug"] == "existing-author"
    assert payload.get("status") != "CONNECTED"
