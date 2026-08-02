from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .wordpress_com_auth import WordPressComConfig
from .wordpress_com_client import WordPressComClient


def config_from_environment() -> WordPressComConfig:
    return WordPressComConfig(
        site_identifier=os.environ.get(
            "WORDPRESS_COM_SITE_IDENTIFIER",
            "",
        ),
        access_token=os.environ.get(
            "WORDPRESS_COM_ACCESS_TOKEN",
            "",
        ),
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
    client = WordPressComClient(
        config_from_environment()
    )

    if args.command == "site":
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
