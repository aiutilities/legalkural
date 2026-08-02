from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .wordpress_client import WordPressClient
from .wordpress_models import WordPressConfig


def config_from_environment() -> WordPressConfig:
    return WordPressConfig(
        site_url=os.environ.get(
            "WORDPRESS_SITE_URL",
            "",
        ),
        username=os.environ.get(
            "WORDPRESS_USERNAME",
            "",
        ),
        application_password=os.environ.get(
            "WORDPRESS_APPLICATION_PASSWORD",
            "",
        ),
        verify_ssl=os.environ.get(
            "WORDPRESS_VERIFY_SSL",
            "true",
        ).lower()
        not in {
            "0",
            "false",
            "no",
        },
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
        retry_delay_seconds=float(
            os.environ.get(
                "WORDPRESS_RETRY_DELAY_SECONDS",
                "1",
            )
        ),
    )


def read_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="legalkural-wordpress",
        description="LegalKural WordPress REST client.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser("doctor")
    subparsers.add_parser("me")

    create = subparsers.add_parser("create")
    create.add_argument("payload", type=Path)

    update = subparsers.add_parser("update")
    update.add_argument("post_id", type=int)
    update.add_argument("payload", type=Path)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    client = WordPressClient(config_from_environment())

    if args.command == "doctor":
        output = client.health()
    elif args.command == "me":
        output = client.current_user()
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
