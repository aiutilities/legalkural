from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .wordpress_com_auth import WordPressComConfig
from .wordpress_com_client import WordPressComClient
from .wordpress_com_oauth import (
    OAuthApplication,
    delete_token,
    load_token,
    login,
)


TOKEN_PATH = Path(
    os.environ.get(
        "WORDPRESS_COM_TOKEN_FILE",
        "generated/wordpress/oauth.json",
    )
)


def resolved_access_token() -> str:
    value = os.environ.get(
        "WORDPRESS_COM_ACCESS_TOKEN",
        "",
    ).strip()

    if value:
        return value

    if TOKEN_PATH.exists():
        return load_token(TOKEN_PATH).access_token

    return ""


def config_from_environment() -> WordPressComConfig:
    return WordPressComConfig(
        site_identifier=os.environ.get(
            "WORDPRESS_COM_SITE_IDENTIFIER",
            "",
        ),
        access_token=resolved_access_token(),
        timeout_seconds=float(
            os.environ.get(
                "WORDPRESS_TIMEOUT_SECONDS",
                "30",
            )
        ),
        max_attempts=int(
            os.environ.get(
                "WORDPRESS_MAX_ATTEMPTS",
                "3",
            )
        ),
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="legalkural-wordpress-com",
        description="LegalKural WordPress.com adapter.",
    )
    sub = value.add_subparsers(
        dest="command",
        required=True,
    )

    login_parser = sub.add_parser("login")
    login_parser.add_argument(
        "--no-browser",
        action="store_true",
    )

    sub.add_parser("logout")
    sub.add_parser("whoami")
    sub.add_parser("site")

    posts = sub.add_parser("posts")
    posts.add_argument(
        "--per-page",
        type=int,
        default=5,
    )

    create = sub.add_parser("create")
    create.add_argument("payload", type=Path)

    update = sub.add_parser("update")
    update.add_argument("post_id", type=int)
    update.add_argument("payload", type=Path)

    return value


def read_payload(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def main() -> int:
    args = parser().parse_args()

    if args.command == "login":
        client_id = os.environ.get(
            "WORDPRESS_COM_CLIENT_ID",
            "",
        ).strip()
        client_secret = os.environ.get(
            "WORDPRESS_COM_CLIENT_SECRET",
            "",
        ).strip()
        redirect_uri = os.environ.get(
            "WORDPRESS_COM_REDIRECT_URI",
            "http://localhost:8080/callback",
        ).strip()

        if not client_id or not client_secret:
            raise SystemExit(
                "ERROR: Set WORDPRESS_COM_CLIENT_ID "
                "and WORDPRESS_COM_CLIENT_SECRET."
            )

        token = login(
            OAuthApplication(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
            ),
            TOKEN_PATH,
            open_browser=not args.no_browser,
        )
        print(
            json.dumps(
                {
                    "status": "AUTHENTICATED",
                    "token_file": str(TOKEN_PATH),
                    "blog_id": token.blog_id,
                    "blog_url": token.blog_url,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "logout":
        removed = delete_token(TOKEN_PATH)
        print(
            json.dumps(
                {
                    "status": (
                        "LOGGED_OUT"
                        if removed
                        else "NO_TOKEN"
                    ),
                    "token_file": str(TOKEN_PATH),
                },
                indent=2,
            )
        )
        return 0

    client = WordPressComClient(
        config_from_environment()
    )

    if args.command == "whoami":
        output = client.site()
    elif args.command == "site":
        output = client.site()
    elif args.command == "posts":
        output = client.posts(
            per_page=args.per_page,
            context="edit",
        )
    elif args.command == "create":
        output = client.create_post(
            read_payload(args.payload)
        )
    else:
        output = client.update_post(
            args.post_id,
            read_payload(args.payload),
        )

    print(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
