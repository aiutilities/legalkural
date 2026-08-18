"""Production workspace contract for offline LegalKural operations."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from jsonschema import Draft202012Validator


OPERATIONS_WORKSPACE_SCHEMA_VERSION = "1.0"
WORKSPACE_MANIFEST = "workspace.json"
WORKSPACE_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*$")
PATH_NAMES = (
    "generated_evidence",
    "candidates",
    "editions",
    "archive",
    "backups",
    "runtime_evidence",
    "operator_logs",
)
DEFAULT_DIRECTORIES = {
    "generated_evidence": "generated-evidence",
    "candidates": "candidates",
    "editions": "editions",
    "archive": "archive",
    "backups": "backups",
    "runtime_evidence": "runtime-evidence",
    "operator_logs": "operator-logs",
}


class OperationsWorkspaceError(ValueError):
    """Raised when a production workspace is unsafe or invalid."""


def _schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "schemas"
        / "production_workspace.schema.json"
    )


def _schema() -> dict[str, Any]:
    with _schema_path().open(encoding="utf-8") as handle:
        return json.load(handle)


def _reject_symlink_chain(path: Path, field: str) -> None:
    candidate = path
    while True:
        if candidate.is_symlink():
            raise OperationsWorkspaceError(f"{field} cannot contain a symlink")
        if candidate.parent == candidate:
            return
        candidate = candidate.parent


def _absolute_path(value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise OperationsWorkspaceError(f"{field} must be non-empty text")
    supplied = Path(value).expanduser()
    if not supplied.is_absolute():
        raise OperationsWorkspaceError(f"{field} must be an absolute path")
    _reject_symlink_chain(supplied, field)
    return supplied.resolve()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_production_workspace(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and normalize one production-workspace manifest."""

    if not isinstance(payload, Mapping):
        raise OperationsWorkspaceError("workspace payload must be an object")

    value = deepcopy(dict(payload))
    errors = sorted(
        Draft202012Validator(_schema()).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        message = errors[0].message
        raise OperationsWorkspaceError(f"workspace schema validation failed: {message}")

    workspace_id = value["workspace_id"]
    if not WORKSPACE_ID_PATTERN.fullmatch(workspace_id):
        raise OperationsWorkspaceError("workspace_id has an invalid format")

    root = _absolute_path(value["workspace_root"], "workspace_root")
    paths = value["paths"]
    resolved: dict[str, Path] = {}

    for name in PATH_NAMES:
        path = _absolute_path(paths[name], f"paths.{name}")
        if path == root or not _is_relative_to(path, root):
            raise OperationsWorkspaceError(
                f"paths.{name} must be a strict descendant of workspace_root"
            )
        resolved[name] = path

    items = list(resolved.items())
    for index, (left_name, left) in enumerate(items):
        for right_name, right in items[index + 1 :]:
            if (
                left == right
                or _is_relative_to(left, right)
                or _is_relative_to(right, left)
            ):
                raise OperationsWorkspaceError(
                    f"workspace paths overlap: {left_name} and {right_name}"
                )

    value["workspace_root"] = str(root)
    value["paths"] = {
        name: str(resolved[name])
        for name in PATH_NAMES
    }
    return value


def initialize_production_workspace(
    workspace_root: Path,
    workspace_id: str,
) -> dict[str, Any]:
    """Atomically initialize one empty caller-approved workspace."""

    supplied = workspace_root.expanduser()
    if not supplied.is_absolute():
        raise OperationsWorkspaceError("workspace_root must be an absolute path")
    _reject_symlink_chain(supplied, "workspace_root")
    root = supplied.resolve()

    if root.exists():
        if not root.is_dir():
            raise OperationsWorkspaceError("workspace_root must be a directory")
        if any(root.iterdir()):
            raise OperationsWorkspaceError("workspace_root must be empty")
    else:
        root.mkdir(parents=True)

    payload = {
        "schema_version": OPERATIONS_WORKSPACE_SCHEMA_VERSION,
        "workspace_id": workspace_id,
        "workspace_root": str(root),
        "paths": {
            name: str(root / DEFAULT_DIRECTORIES[name])
            for name in PATH_NAMES
        },
    }
    validated = validate_production_workspace(payload)

    created: list[Path] = []
    temporary_path: Path | None = None
    try:
        for value in validated["paths"].values():
            directory = Path(value)
            directory.mkdir()
            created.append(directory)

        descriptor, temporary = tempfile.mkstemp(
            prefix=".workspace.", suffix=".tmp", dir=root
        )
        temporary_path = Path(temporary)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(validated, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, root / WORKSPACE_MANIFEST)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        for directory in reversed(created):
            directory.rmdir()
        root.rmdir()
        raise

    return deepcopy(validated)


def load_production_workspace(workspace_root: Path) -> dict[str, Any]:
    """Load a complete initialized workspace and revalidate its paths."""

    supplied = workspace_root.expanduser()
    if not supplied.is_absolute():
        raise OperationsWorkspaceError("workspace_root must be an absolute path")
    _reject_symlink_chain(supplied, "workspace_root")
    root = supplied.resolve()
    manifest = root / WORKSPACE_MANIFEST
    if manifest.is_symlink() or not manifest.is_file():
        raise OperationsWorkspaceError("workspace manifest is missing or unsafe")

    try:
        with manifest.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise OperationsWorkspaceError("workspace manifest is unreadable") from exc

    validated = validate_production_workspace(payload)
    if Path(validated["workspace_root"]) != root:
        raise OperationsWorkspaceError("workspace manifest root does not match")
    for name, value in validated["paths"].items():
        directory = Path(value)
        if directory.is_symlink() or not directory.is_dir():
            raise OperationsWorkspaceError(
                f"workspace path is missing or unsafe: {name}"
            )
    return validated
