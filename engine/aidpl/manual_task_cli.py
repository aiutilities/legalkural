from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .manual_tasks import (
    VALID_STATUSES,
    cancel_task,
    complete_task,
    get_task,
    list_tasks,
)


def print_json(payload: Any) -> None:
    print(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-manual-task",
        description=(
            "Inspect and record completion of LegalKural manual tasks."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    list_parser = subparsers.add_parser(
        "list",
        help="List manual tasks.",
    )
    list_parser.add_argument(
        "--case-root",
        type=Path,
        required=True,
    )
    list_parser.add_argument(
        "--status",
        choices=sorted(VALID_STATUSES),
    )

    show_parser = subparsers.add_parser(
        "show",
        help="Show one manual task.",
    )
    show_parser.add_argument(
        "--case-root",
        type=Path,
        required=True,
    )
    show_parser.add_argument(
        "--task-id",
        required=True,
    )

    complete_parser = subparsers.add_parser(
        "complete",
        help="Record completion of an OPEN manual task.",
    )
    complete_parser.add_argument(
        "--case-root",
        type=Path,
        required=True,
    )
    complete_parser.add_argument(
        "--task-id",
        required=True,
    )
    complete_parser.add_argument(
        "--completed-by",
        required=True,
    )
    complete_parser.add_argument(
        "--note",
        required=True,
    )

    cancel_parser = subparsers.add_parser(
        "cancel",
        help="Cancel an OPEN manual task.",
    )
    cancel_parser.add_argument(
        "--case-root",
        type=Path,
        required=True,
    )
    cancel_parser.add_argument(
        "--task-id",
        required=True,
    )
    cancel_parser.add_argument(
        "--completed-by",
        required=True,
    )
    cancel_parser.add_argument(
        "--note",
        required=True,
    )

    return parser


def run(args: argparse.Namespace) -> dict[str, Any] | list[dict[str, Any]]:
    if args.command == "list":
        return list_tasks(
            args.case_root,
            status=args.status,
        )

    if args.command == "show":
        return get_task(
            args.case_root,
            args.task_id,
        )

    if args.command == "complete":
        return complete_task(
            case_root=args.case_root,
            task_id=args.task_id,
            completed_by=args.completed_by,
            completion_note=args.note,
        )

    if args.command == "cancel":
        return cancel_task(
            case_root=args.case_root,
            task_id=args.task_id,
            completed_by=args.completed_by,
            completion_note=args.note,
        )

    raise ValueError(
        f"Unsupported manual-task command: {args.command}"
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = run(args)
        print_json(result)
        return 0
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
