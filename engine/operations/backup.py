"""Atomic, deterministic production-workspace backups."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Mapping
import zipfile

from jsonschema import Draft202012Validator

from .integrity import audit_production_estate
from .workspace import load_production_workspace

BACKUP_SCHEMA_VERSION = "1.0"
BACKUP_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*$")
BACKUP_ZIP = "backup.zip"
BACKUP_EVIDENCE = "backup-evidence.json"
EXCLUDED_PATH = "backups"


class ProductionBackupError(ValueError):
    """Raised when a production backup cannot be safely completed."""


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _schema() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "schemas" / "production_backup_evidence.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def compute_backup_evidence_sha256(evidence: Mapping[str, Any]) -> str:
    value = deepcopy(dict(evidence))
    value.pop("evidence_sha256", None)
    return _sha256_bytes(_canonical(value))


def validate_production_backup_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        raise ProductionBackupError("backup evidence must be an object")
    value = deepcopy(dict(evidence))
    errors = sorted(Draft202012Validator(_schema()).iter_errors(value), key=lambda e: list(e.absolute_path))
    if errors:
        raise ProductionBackupError(f"backup evidence is invalid: {errors[0].message}")
    if value["evidence_sha256"] != compute_backup_evidence_sha256(value):
        raise ProductionBackupError("backup evidence sha256 does not match content")
    return value


def _utc(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ProductionBackupError("created_at_utc is invalid") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ProductionBackupError("created_at_utc must be UTC")
    return value


def _inventory(root: Path, workspace: Mapping[str, Any]) -> list[dict[str, Any]]:
    sources = [(root / "workspace.json", "workspace.json")]
    for name, value in sorted(workspace["paths"].items()):
        if name == EXCLUDED_PATH:
            continue
        base = Path(value)
        if base.is_symlink() or not base.is_dir():
            raise ProductionBackupError(f"backup source is missing or unsafe: {name}")
        for path in sorted(base.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
            if path.is_symlink():
                raise ProductionBackupError(f"backup source cannot contain symlink: {path}")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ProductionBackupError(f"backup source contains unsupported entry: {path}")
            sources.append((path, path.relative_to(root).as_posix()))
    result = []
    for path, relative in sources:
        data = path.read_bytes()
        result.append({"path": relative, "byte_count": len(data), "sha256": _sha256_bytes(data)})
    result.sort(key=lambda item: item["path"])
    return result


def _write_zip(output: Path, root: Path, files: list[dict[str, Any]]) -> None:
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for item in files:
            info = zipfile.ZipInfo(item["path"], date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (root / item["path"]).read_bytes())
    with output.open("rb") as handle:
        os.fsync(handle.fileno())


def verify_production_backup(backup_directory: Path) -> dict[str, Any]:
    """Verify immutable evidence plus every ZIP member, size and digest."""
    supplied = backup_directory.expanduser()
    if supplied.is_symlink():
        raise ProductionBackupError("backup directory cannot be a symlink")
    directory = supplied.resolve()
    if not directory.is_dir():
        raise ProductionBackupError("backup directory is missing")
    entries = {entry.name: entry for entry in directory.iterdir()}
    if set(entries) != {BACKUP_ZIP, BACKUP_EVIDENCE}:
        raise ProductionBackupError("backup directory is incomplete")
    if any(entry.is_symlink() or not entry.is_file() for entry in entries.values()):
        raise ProductionBackupError("backup files are unsafe")
    try:
        evidence = validate_production_backup_evidence(
            json.loads(entries[BACKUP_EVIDENCE].read_text(encoding="utf-8"))
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionBackupError("backup evidence is unreadable") from exc
    archive_bytes = entries[BACKUP_ZIP].read_bytes()
    if len(archive_bytes) != evidence["archive_byte_count"]:
        raise ProductionBackupError("backup archive byte count does not match")
    if _sha256_bytes(archive_bytes) != evidence["archive_sha256"]:
        raise ProductionBackupError("backup archive sha256 does not match")
    expected = {item["path"]: item for item in evidence["files"]}
    try:
        with zipfile.ZipFile(entries[BACKUP_ZIP]) as archive:
            names = archive.namelist()
            if names != sorted(expected) or len(names) != len(set(names)):
                raise ProductionBackupError("backup archive members do not match evidence")
            for name in names:
                if name.startswith("/") or ".." in Path(name).parts or chr(92) in name:
                    raise ProductionBackupError("backup archive member path is unsafe")
                data = archive.read(name)
                if len(data) != expected[name]["byte_count"]:
                    raise ProductionBackupError("backup member byte count does not match")
                if _sha256_bytes(data) != expected[name]["sha256"]:
                    raise ProductionBackupError("backup member sha256 does not match")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ProductionBackupError("backup archive is unreadable") from exc
    return evidence


def create_production_backup(*, workspace_root: Path, backup_id: str, created_at_utc: str) -> dict[str, Any]:
    """Create one immutable backup after a passing integrity audit."""
    if not isinstance(backup_id, str) or not BACKUP_ID_PATTERN.fullmatch(backup_id):
        raise ProductionBackupError("backup_id is invalid")
    _utc(created_at_utc)
    workspace = load_production_workspace(workspace_root)
    audit = audit_production_estate(workspace_root)
    if audit["status"] != "PASS":
        raise ProductionBackupError("production integrity audit did not pass")
    root = Path(workspace["workspace_root"])
    backups = Path(workspace["paths"]["backups"])
    target = backups / backup_id
    if target.exists() or target.is_symlink():
        raise ProductionBackupError(f"backup_id already exists: {backup_id}")
    before = _inventory(root, workspace)
    temporary = Path(tempfile.mkdtemp(prefix=".backup-tmp-", dir=backups))
    try:
        zip_path = temporary / BACKUP_ZIP
        _write_zip(zip_path, root, before)
        after = _inventory(root, workspace)
        if after != before:
            raise ProductionBackupError("backup source changed during capture")
        zip_bytes = zip_path.read_bytes()
        evidence = {
            "schema_version": BACKUP_SCHEMA_VERSION,
            "backup_id": backup_id,
            "workspace_id": workspace["workspace_id"],
            "created_at_utc": created_at_utc,
            "status": "COMPLETE",
            "archive_file": BACKUP_ZIP,
            "archive_byte_count": len(zip_bytes),
            "archive_sha256": _sha256_bytes(zip_bytes),
            "file_count": len(before),
            "files": before,
            "excluded_workspace_paths": [EXCLUDED_PATH],
            "provider_requests": 0,
            "wordpress_requests": 0,
            "tamil_rendered": False,
            "thirukkural_algorithm_usage": "TITLE_ONLY",
        }
        evidence["evidence_sha256"] = compute_backup_evidence_sha256(evidence)
        validate_production_backup_evidence(evidence)
        evidence_path = temporary / BACKUP_EVIDENCE
        with evidence_path.open("x", encoding="utf-8") as handle:
            json.dump(evidence, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(temporary, target)
        descriptor = os.open(backups, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return verify_production_backup(target)
