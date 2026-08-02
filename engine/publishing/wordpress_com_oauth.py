from __future__ import annotations

import json
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any


class OAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class OAuthApplication:
    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8080/callback"


@dataclass(frozen=True)
class OAuthToken:
    access_token: str
    blog_id: str | None = None
    blog_url: str | None = None
    token_type: str | None = None
    scope: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "blog_id": self.blog_id,
            "blog_url": self.blog_url,
            "token_type": self.token_type,
            "scope": self.scope,
        }


def authorization_url(
    app: OAuthApplication,
    state: str,
) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": app.client_id,
            "redirect_uri": app.redirect_uri,
            "response_type": "code",
            "scope": "global",
            "state": state,
        }
    )
    return (
        "https://public-api.wordpress.com/oauth2/authorize?"
        f"{query}"
    )


def exchange_code(
    app: OAuthApplication,
    code: str,
) -> OAuthToken:
    body = urllib.parse.urlencode(
        {
            "client_id": app.client_id,
            "client_secret": app.client_secret,
            "redirect_uri": app.redirect_uri,
            "grant_type": "authorization_code",
            "code": code,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        "https://public-api.wordpress.com/oauth2/token",
        data=body,
        headers={
            "Content-Type": (
                "application/x-www-form-urlencoded"
            ),
            "Accept": "application/json",
            "User-Agent": "LegalKural/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=60,
        ) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )
    except Exception as exc:
        raise OAuthError(
            f"OAuth token exchange failed: {exc}"
        ) from exc

    token = payload.get("access_token")

    if not isinstance(token, str) or not token:
        raise OAuthError(
            "OAuth response did not include access_token."
        )

    return OAuthToken(
        access_token=token,
        blog_id=(
            str(payload["blog_id"])
            if payload.get("blog_id") is not None
            else None
        ),
        blog_url=payload.get("blog_url"),
        token_type=payload.get("token_type"),
        scope=payload.get("scope"),
    )


def save_token(
    token: OAuthToken,
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            token.to_dict(),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def load_token(path: Path) -> OAuthToken:
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )
    token = payload.get("access_token")

    if not isinstance(token, str) or not token:
        raise OAuthError(
            "Stored OAuth token is invalid."
        )

    return OAuthToken(
        access_token=token,
        blog_id=payload.get("blog_id"),
        blog_url=payload.get("blog_url"),
        token_type=payload.get("token_type"),
        scope=payload.get("scope"),
    )


def delete_token(path: Path) -> bool:
    if not path.exists():
        return False

    path.unlink()
    return True


def login(
    app: OAuthApplication,
    token_path: Path,
    *,
    open_browser: bool = True,
) -> OAuthToken:
    parsed = urllib.parse.urlparse(
        app.redirect_uri
    )

    if parsed.hostname not in {
        "localhost",
        "127.0.0.1",
    }:
        raise OAuthError(
            "OAuth callback must use localhost "
            "or 127.0.0.1."
        )

    if parsed.scheme != "http":
        raise OAuthError(
            "Local OAuth callback must use http."
        )

    port = parsed.port or 80
    callback_path = parsed.path or "/"
    state = secrets.token_urlsafe(32)
    result: dict[str, str] = {}
    completed = threading.Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            request_url = urllib.parse.urlparse(
                self.path
            )

            if request_url.path != callback_path:
                self.send_response(404)
                self.end_headers()
                return

            query = urllib.parse.parse_qs(
                request_url.query
            )

            if query.get("state", [""])[0] != state:
                result["error"] = "OAuth state mismatch."
            elif "error" in query:
                result["error"] = query["error"][0]
            elif "code" not in query:
                result["error"] = (
                    "Authorization code missing."
                )
            else:
                result["code"] = query["code"][0]

            body = (
                "<html><body><h2>LegalKural "
                "WordPress.com authorization complete."
                "</h2><p>You may close this tab and "
                "return to Terminal.</p></body></html>"
            ).encode("utf-8")

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8",
            )
            self.send_header(
                "Content-Length",
                str(len(body)),
            )
            self.end_headers()
            self.wfile.write(body)
            completed.set()

        def log_message(
            self,
            _format: str,
            *_args: object,
        ) -> None:
            return

    server = HTTPServer(
        (parsed.hostname or "localhost", port),
        CallbackHandler,
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    url = authorization_url(app, state)

    print("Open this URL if the browser does not open:")
    print(url)
    print()
    print("Waiting for WordPress.com authorization...")

    if open_browser:
        webbrowser.open(url)

    if not completed.wait(timeout=300):
        server.shutdown()
        server.server_close()
        raise OAuthError(
            "Timed out waiting for OAuth callback."
        )

    server.shutdown()
    server.server_close()

    if "error" in result:
        raise OAuthError(result["error"])

    token = exchange_code(
        app,
        result["code"],
    )
    save_token(token, token_path)
    return token
