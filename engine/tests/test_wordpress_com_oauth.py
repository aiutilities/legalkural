from pathlib import Path

from publishing.wordpress_com_oauth import (
    OAuthApplication,
    OAuthToken,
    authorization_url,
    delete_token,
    load_token,
    save_token,
)


def test_authorization_url() -> None:
    url = authorization_url(
        OAuthApplication(
            client_id="144954",
            client_secret="secret",
        ),
        "state-value",
    )

    assert "client_id=144954" in url
    assert "response_type=code" in url
    assert "state=state-value" in url
    assert "localhost%3A8080" in url


def test_token_storage(tmp_path: Path) -> None:
    path = tmp_path / "oauth.json"
    token = OAuthToken(
        access_token="token",
        blog_id="123",
        blog_url="https://example.wordpress.com",
    )

    save_token(token, path)

    assert path.exists()
    assert load_token(path).access_token == "token"
    assert load_token(path).blog_id == "123"


def test_delete_token(tmp_path: Path) -> None:
    path = tmp_path / "oauth.json"
    path.write_text("{}", encoding="utf-8")

    assert delete_token(path) is True
    assert delete_token(path) is False
