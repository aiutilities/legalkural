"""Command-line interface for offline LegalKural production operations."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .backup import create_production_backup, verify_production_backup
from .integrity import audit_production_estate
from .ledger import (
    begin_operation, complete_operation, fail_operation, inspect_operation,
    list_operations, plan_operation_resume, record_operation_checkpoint,
)
from .restore import restore_production_backup
from .workspace import initialize_production_workspace


def _path(parser: argparse.ArgumentParser, name: str, *, required: bool = True) -> None:
    parser.add_argument(name, type=Path, required=required)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="legalkural-operations")
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("workspace-init")
    _path(command, "--workspace-root")
    command.add_argument("--workspace-id", required=True)

    command = commands.add_parser("audit")
    _path(command, "--workspace-root")

    command = commands.add_parser("backup-create")
    _path(command, "--workspace-root")
    command.add_argument("--backup-id", required=True)
    command.add_argument("--created-at-utc", required=True)

    command = commands.add_parser("backup-verify")
    _path(command, "--backup-directory")

    command = commands.add_parser("restore")
    _path(command, "--backup-directory")
    _path(command, "--destination-root")
    command.add_argument("--restore-id", required=True)
    command.add_argument("--restored-at-utc", required=True)

    command = commands.add_parser("operation-begin")
    _path(command, "--workspace-root")
    command.add_argument("--operation-id", required=True)
    command.add_argument(
        "--operation-type", required=True,
        choices=("INTEGRITY_AUDIT", "BACKUP", "RESTORE"),
    )
    command.add_argument("--actor", required=True)
    command.add_argument("--occurred-at-utc", required=True)
    _path(command, "--inputs-json-file")

    command = commands.add_parser("operation-checkpoint")
    _path(command, "--workspace-root")
    command.add_argument("--operation-id", required=True)
    command.add_argument("--occurred-at-utc", required=True)
    _path(command, "--checkpoint-json-file")

    command = commands.add_parser("operation-complete")
    _path(command, "--workspace-root")
    command.add_argument("--operation-id", required=True)
    command.add_argument("--occurred-at-utc", required=True)
    _path(command, "--result-json-file")

    command = commands.add_parser("operation-fail")
    _path(command, "--workspace-root")
    command.add_argument("--operation-id", required=True)
    command.add_argument("--occurred-at-utc", required=True)
    command.add_argument("--error", required=True)

    for name in ("operation-inspect", "operation-resume-plan"):
        command = commands.add_parser(name)
        _path(command, "--workspace-root")
        command.add_argument("--operation-id", required=True)

    command = commands.add_parser("operation-list")
    _path(command, "--workspace-root")
    return parser


def _object_file(path: Path, label: str) -> dict[str, Any]:
    supplied = path.expanduser()
    if supplied.is_symlink() or not supplied.is_file():
        raise ValueError(f"{label} must be a real JSON file")
    try:
        value = json.loads(supplied.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _execute(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "workspace-init":
        return initialize_production_workspace(args.workspace_root, args.workspace_id)
    if args.command == "audit":
        return audit_production_estate(args.workspace_root)
    if args.command == "backup-create":
        return create_production_backup(
            workspace_root=args.workspace_root, backup_id=args.backup_id,
            created_at_utc=args.created_at_utc,
        )
    if args.command == "backup-verify":
        return verify_production_backup(args.backup_directory)
    if args.command == "restore":
        return restore_production_backup(
            backup_directory=args.backup_directory,
            destination_root=args.destination_root,
            restore_id=args.restore_id, restored_at_utc=args.restored_at_utc,
        )
    if args.command == "operation-begin":
        return begin_operation(
            workspace_root=args.workspace_root, operation_id=args.operation_id,
            operation_type=args.operation_type, actor=args.actor,
            occurred_at_utc=args.occurred_at_utc,
            inputs=_object_file(args.inputs_json_file, "inputs_json_file"),
        )
    if args.command == "operation-checkpoint":
        return record_operation_checkpoint(
            workspace_root=args.workspace_root, operation_id=args.operation_id,
            occurred_at_utc=args.occurred_at_utc,
            checkpoint=_object_file(args.checkpoint_json_file, "checkpoint_json_file"),
        )
    if args.command == "operation-complete":
        return complete_operation(
            workspace_root=args.workspace_root, operation_id=args.operation_id,
            occurred_at_utc=args.occurred_at_utc,
            result=_object_file(args.result_json_file, "result_json_file"),
        )
    if args.command == "operation-fail":
        return fail_operation(
            workspace_root=args.workspace_root, operation_id=args.operation_id,
            occurred_at_utc=args.occurred_at_utc, error=args.error,
        )
    if args.command == "operation-inspect":
        return inspect_operation(args.workspace_root, args.operation_id)
    if args.command == "operation-list":
        return list_operations(args.workspace_root)
    if args.command == "operation-resume-plan":
        return plan_operation_resume(args.workspace_root, args.operation_id)
    raise ValueError(f"unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        result = _execute(args)
    except (ValueError, OSError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
