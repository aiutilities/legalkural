"""Command-line interface for the offline LegalKural journal workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .discovery import discover_articles
from .workflow import build_weekly_journal, verify_journal_edition


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="legalkural-journal")
    commands = parser.add_subparsers(dest="command", required=True)

    discover = commands.add_parser("discover")
    discover.add_argument(
        "--generated-root",
        type=Path,
        default=Path("generated"),
    )

    build = commands.add_parser("build")
    build.add_argument("--project-root", type=Path, default=Path("."))
    build.add_argument(
        "--generated-root",
        type=Path,
        default=Path("generated"),
    )
    build.add_argument("--output-root", type=Path, required=True)
    build.add_argument("--journal-id", required=True)
    build.add_argument("--edition-date", required=True)
    build.add_argument("--title", required=True)
    build.add_argument("--selected-by", required=True)
    build.add_argument("--finalized-at-utc", required=True)
    build.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        required=True,
    )

    verify = commands.add_parser("verify")
    verify.add_argument(
        "--edition-directory",
        type=Path,
        required=True,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "discover":
        result = discover_articles(args.generated_root)
    elif args.command == "build":
        result = build_weekly_journal(
            project_root=args.project_root,
            generated_root=args.generated_root,
            output_root=args.output_root,
            journal_id=args.journal_id,
            edition_date=args.edition_date,
            title=args.title,
            selected_by=args.selected_by,
            finalized_at_utc=args.finalized_at_utc,
            case_ids=args.case_ids,
        )
    else:
        result = verify_journal_edition(args.edition_directory)

    json.dump(
        result,
        sys.stdout,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
