"""Verified, atomic restoration of LegalKural production backups."""
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

from .backup import ProductionBackupError, verify_production_backup
from .integrity import audit_production_estate
from .workspace import DEFAULT_DIRECTORIES, validate_production_workspace

RESTORE_SCHEMA_VERSION = "1.0"
RESTORE_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*$")


class ProductionRestoreError(ValueError):
    """Raised when a production restore cannot be completed safely."""


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _schema() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "schemas" / "production_restore_evidence.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def compute_restore_evidence_sha256(evidence: Mapping[str, Any]) -> str:
    value = deepcopy(dict(evidence))
    value.pop("evidence_sha256", None)
    return _sha(_canonical(value))


def validate_production_restore_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        raise ProductionRestoreError("restore evidence must be an object")
    value = deepcopy(dict(evidence))
    errors = sorted(Draft202012Validator(_schema()).iter_errors(value), key=lambda e: list(e.absolute_path))
    if errors:
        raise ProductionRestoreError(f"restore evidence is invalid: {errors[0].message}")
    if value["evidence_sha256"] != compute_restore_evidence_sha256(value):
        raise ProductionRestoreError("restore evidence sha256 does not match content")
    return value


def _utc(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ProductionRestoreError("restored_at_utc is invalid") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ProductionRestoreError("restored_at_utc must be UTC")
    return value


def _safe_destination(destination: Path) -> Path:
    supplied = destination.expanduser()
    if not supplied.is_absolute():
        raise ProductionRestoreError("destination_root must be absolute")
    if supplied.exists() or supplied.is_symlink():
        raise ProductionRestoreError("destination_root must not already exist")
    parent = supplied.parent
    if parent.is_symlink() or not parent.is_dir():
        raise ProductionRestoreError("destination parent is missing or unsafe")
    cursor = parent
    while cursor != cursor.parent:
        if cursor.is_symlink():
            raise ProductionRestoreError("destination path cannot contain a symlink")
        cursor = cursor.parent
    return supplied


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def restore_production_backup(*, backup_directory: Path, destination_root: Path, restore_id: str, restored_at_utc: str) -> dict[str, Any]:
    """Restore one verified backup into a new absolute destination."""
    if not isinstance(restore_id, str) or not RESTORE_ID_PATTERN.fullmatch(restore_id):
        raise ProductionRestoreError("restore_id is invalid")
    _utc(restored_at_utc)
    destination = _safe_destination(destination_root)
    try:
        backup = verify_production_backup(backup_directory)
    except ProductionBackupError as exc:
        raise ProductionRestoreError(f"backup is not verified: {exc}") from exc
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}-restore-tmp-", dir=destination.parent))
    try:
        for directory in DEFAULT_DIRECTORIES.values():
            (temporary / directory).mkdir()
        expected = {item["path"]: item for item in backup["files"]}
        archive_path = Path(backup_directory).resolve() / backup["archive_file"]
        with zipfile.ZipFile(archive_path) as archive:
            member_names = archive.namelist()
            if len(member_names) != len(set(member_names)):
                raise ProductionRestoreError("backup archive contains duplicate members")
            for name in member_names:
                parts = Path(name).parts
                if name not in expected or name.startswith("/") or ".." in parts or chr(92) in name:
                    raise ProductionRestoreError("backup archive member is unsafe or undeclared")
                if parts[0] == DEFAULT_DIRECTORIES["backups"]:
                    raise ProductionRestoreError("backup archive cannot restore backup storage")
                data = archive.read(name)
                if len(data) != expected[name]["byte_count"] or _sha(data) != expected[name]["sha256"]:
                    raise ProductionRestoreError("restored member does not match backup evidence")
                _write(temporary / name, data)
        restored_paths = [path for path in temporary.rglob("*") if path.is_file()]
        if {path.relative_to(temporary).as_posix() for path in restored_paths} != set(expected):
            raise ProductionRestoreError("restored file set does not match backup evidence")
        manifest_path = temporary / "workspace.json"
        original_manifest = manifest_path.read_bytes()
        manifest = json.loads(original_manifest)
        manifest["workspace_root"] = destination.as_posix()
        manifest["paths"] = {
            name: (destination / relative).as_posix()
            for name, relative in DEFAULT_DIRECTORIES.items()
        }
        validate_production_workspace(manifest)
        rebased = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
        manifest_path.unlink()
        _write(manifest_path, rebased)
        evidence = {
            "schema_version": RESTORE_SCHEMA_VERSION,
            "restore_id": restore_id,
            "backup_id": backup["backup_id"],
            "backup_evidence_sha256": backup["evidence_sha256"],
            "workspace_id": backup["workspace_id"],
            "destination_root": destination.as_posix(),
            "restored_at_utc": restored_at_utc,
            "status": "VERIFIED",
            "restored_file_count": len(expected),
            "original_manifest_sha256": _sha(original_manifest),
            "rebased_manifest_sha256": _sha(rebased),
            "integrity_status": "PASS",
            "provider_requests": 0,
            "wordpress_requests": 0,
            "tamil_rendered": False,
            "thirukkural_algorithm_usage": "TITLE_ONLY",
        }
        evidence["evidence_sha256"] = compute_restore_evidence_sha256(evidence)
        validate_production_restore_evidence(evidence)
        evidence_path = temporary / DEFAULT_DIRECTORIES["runtime_evidence"] / f"restore-{restore_id}.json"
        _write(evidence_path, json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n")
        # Audit against temporary-root paths, then restore the final rebased manifest.
        audit_manifest = deepcopy(manifest)
        audit_manifest["workspace_root"] = temporary.as_posix()
        audit_manifest["paths"] = {name: (temporary / relative).as_posix() for name, relative in DEFAULT_DIRECTORIES.items()}
        manifest_path.unlink()
        _write(manifest_path, json.dumps(audit_manifest, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n")
        audit = audit_production_estate(temporary)
        if audit["status"] != "PASS":
            raise ProductionRestoreError("restored estate integrity audit did not pass")
        manifest_path.unlink()
        _write(manifest_path, rebased)
        os.rename(temporary, destination)
        descriptor = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return validate_production_restore_evidence(json.loads((destination / DEFAULT_DIRECTORIES["runtime_evidence"] / f"restore-{restore_id}.json").read_text()))
