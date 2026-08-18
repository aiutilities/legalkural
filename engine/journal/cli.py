"""Command-line interface for the offline LegalKural journal workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .archive_store import (
    inspect_archive_entry,
    list_archived_editions,
    register_verified_edition,
    verify_archived_edition,
)
from .candidate import (
    create_candidate_revision,
    revise_candidate,
)
from .candidate_store import (
    list_candidate_revisions,
    load_candidate_revision,
    store_candidate_revision,
)
from .discovery import discover_articles, select_articles
from .finalization import finalize_candidate
from .workflow import (
    build_finalized_candidate_journal,
    build_weekly_journal,
    verify_journal_edition,
)


def _add_case_ids(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        required=True,
        help="Selected case ID; repeat in the intended editorial order.",
    )


def _add_candidate_location(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--storage-root",
        type=Path,
        required=True,
    )
    parser.add_argument("--candidate-id", required=True)


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
    _add_case_ids(build)

    verify = commands.add_parser("verify")
    verify.add_argument(
        "--edition-directory",
        type=Path,
        required=True,
    )

    candidate_create = commands.add_parser("candidate-create")
    _add_candidate_location(candidate_create)
    candidate_create.add_argument(
        "--generated-root",
        type=Path,
        default=Path("generated"),
    )
    candidate_create.add_argument("--journal-id", required=True)
    candidate_create.add_argument("--edition-date", required=True)
    candidate_create.add_argument("--title", required=True)
    candidate_create.add_argument("--editor", required=True)
    candidate_create.add_argument("--revised-at-utc", required=True)
    _add_case_ids(candidate_create)

    candidate_inspect = commands.add_parser("candidate-inspect")
    _add_candidate_location(candidate_inspect)
    candidate_inspect.add_argument("--revision", type=int)

    candidate_list = commands.add_parser("candidate-list")
    _add_candidate_location(candidate_list)

    candidate_revise = commands.add_parser("candidate-revise")
    _add_candidate_location(candidate_revise)
    candidate_revise.add_argument(
        "--generated-root",
        type=Path,
        default=Path("generated"),
    )
    candidate_revise.add_argument("--revised-at-utc", required=True)
    _add_case_ids(candidate_revise)

    candidate_finalize = commands.add_parser("candidate-finalize")
    _add_candidate_location(candidate_finalize)
    candidate_finalize.add_argument(
        "--generated-root",
        type=Path,
        default=Path("generated"),
    )
    candidate_finalize.add_argument("--selected-by", required=True)
    candidate_finalize.add_argument(
        "--finalized-at-utc",
        required=True,
    )

    candidate_build = commands.add_parser("candidate-build")
    candidate_build.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )
    candidate_build.add_argument(
        "--storage-root",
        type=Path,
        required=True,
    )
    candidate_build.add_argument(
        "--output-root",
        type=Path,
        required=True,
    )
    candidate_build.add_argument("--candidate-id", required=True)

    archive_register = commands.add_parser("archive-register")
    archive_register.add_argument(
        "--archive-root",
        type=Path,
        required=True,
    )
    archive_register.add_argument(
        "--edition-directory",
        type=Path,
        required=True,
    )
    archive_register.add_argument(
        "--archived-at-utc",
        required=True,
    )

    archive_list = commands.add_parser("archive-list")
    archive_list.add_argument(
        "--archive-root",
        type=Path,
        required=True,
    )

    archive_inspect = commands.add_parser("archive-inspect")
    archive_inspect.add_argument(
        "--archive-root",
        type=Path,
        required=True,
    )
    archive_inspect.add_argument("--journal-id", required=True)

    archive_verify = commands.add_parser("archive-verify")
    archive_verify.add_argument(
        "--archive-root",
        type=Path,
        required=True,
    )
    archive_verify.add_argument("--journal-id", required=True)

    return parser


def _create_candidate(args: argparse.Namespace) -> dict[str, Any]:
    discovery = discover_articles(args.generated_root)
    selected = select_articles(discovery, args.case_ids)
    candidate = create_candidate_revision(
        candidate_id=args.candidate_id,
        journal_id=args.journal_id,
        edition_date=args.edition_date,
        title=args.title,
        editor=args.editor,
        revised_at_utc=args.revised_at_utc,
        articles=selected,
    )
    result = store_candidate_revision(args.storage_root, candidate)
    result["selected_case_ids"] = [
        article["case_id"] for article in candidate["articles"]
    ]
    return result


def _inspect_candidate(args: argparse.Namespace) -> dict[str, Any]:
    return load_candidate_revision(
        args.storage_root,
        args.candidate_id,
        args.revision,
    )


def _list_candidate(args: argparse.Namespace) -> dict[str, Any]:
    revisions = list_candidate_revisions(
        args.storage_root,
        args.candidate_id,
    )
    return {
        "schema_version": "1.0",
        "candidate_id": args.candidate_id,
        "revision_count": len(revisions),
        "revisions": [
            {
                "revision_number": revision["revision_number"],
                "candidate_sha256": revision["candidate_sha256"],
                "previous_revision_sha256": revision[
                    "previous_revision_sha256"
                ],
                "revised_at_utc": revision["revised_at_utc"],
                "status": revision["status"],
                "selected_case_ids": [
                    article["case_id"]
                    for article in revision["articles"]
                ],
            }
            for revision in revisions
        ],
    }


def _revise_candidate(args: argparse.Namespace) -> dict[str, Any]:
    previous = load_candidate_revision(
        args.storage_root,
        args.candidate_id,
    )
    discovery = discover_articles(args.generated_root)
    selected = select_articles(discovery, args.case_ids)
    revision = revise_candidate(
        previous,
        revised_at_utc=args.revised_at_utc,
        articles=selected,
    )
    result = store_candidate_revision(args.storage_root, revision)
    result["selected_case_ids"] = [
        article["case_id"] for article in revision["articles"]
    ]
    return result


def _finalize_candidate_command(
    args: argparse.Namespace,
) -> dict[str, Any]:
    return finalize_candidate(
        storage_root=args.storage_root,
        generated_root=args.generated_root,
        candidate_id=args.candidate_id,
        selected_by=args.selected_by,
        finalized_at_utc=args.finalized_at_utc,
    )


def _build_candidate_command(args: argparse.Namespace) -> dict:
    return build_finalized_candidate_journal(
        project_root=args.project_root,
        candidate_storage_root=args.storage_root,
        output_root=args.output_root,
        candidate_id=args.candidate_id,
    )


def _register_archive_command(
    args: argparse.Namespace,
) -> dict[str, Any]:
    return register_verified_edition(
        archive_root=args.archive_root,
        edition_directory=args.edition_directory,
        archived_at_utc=args.archived_at_utc,
    )


def _list_archive_command(
    args: argparse.Namespace,
) -> dict[str, Any]:
    return list_archived_editions(args.archive_root)


def _inspect_archive_command(
    args: argparse.Namespace,
) -> dict[str, Any]:
    return inspect_archive_entry(
        args.archive_root,
        args.journal_id,
    )


def _verify_archive_command(
    args: argparse.Namespace,
) -> dict[str, Any]:
    return verify_archived_edition(
        args.archive_root,
        args.journal_id,
    )


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
    elif args.command == "verify":
        result = verify_journal_edition(args.edition_directory)
    elif args.command == "candidate-create":
        result = _create_candidate(args)
    elif args.command == "candidate-inspect":
        result = _inspect_candidate(args)
    elif args.command == "candidate-list":
        result = _list_candidate(args)
    elif args.command == "candidate-revise":
        result = _revise_candidate(args)
    elif args.command == "candidate-finalize":
        result = _finalize_candidate_command(args)
    elif args.command == "candidate-build":
        result = _build_candidate_command(args)
    elif args.command == "archive-register":
        result = _register_archive_command(args)
    elif args.command == "archive-list":
        result = _list_archive_command(args)
    elif args.command == "archive-inspect":
        result = _inspect_archive_command(args)
    else:
        result = _verify_archive_command(args)

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
