"""Read-only production-estate integrity auditing for LegalKural."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from journal.archive_store import (
    JournalArchiveStoreError,
    list_archived_editions,
    verify_archived_edition,
)
from journal.candidate_store import (
    JournalCandidateStoreError,
    list_candidate_revisions,
    load_candidate_finalization,
)
from .workspace import OperationsWorkspaceError, load_production_workspace


REPORT_SCHEMA_VERSION = "1.0"


class ProductionIntegrityError(ValueError):
    """Raised when an integrity report does not satisfy its contract."""


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "schemas" / (
        "production_integrity_report.schema.json"
    )


def _schema() -> dict[str, Any]:
    return json.loads(_schema_path().read_text(encoding="utf-8"))


def validate_production_integrity_report(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ProductionIntegrityError("integrity report must be an object")
    report = deepcopy(dict(payload))
    errors = sorted(
        Draft202012Validator(_schema()).iter_errors(report),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise ProductionIntegrityError(
            f"integrity report is invalid: {errors[0].message}"
        )
    return report


def _finding(code: str, scope: str, message: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": "ERROR",
        "scope": scope,
        "message": message,
    }


def _named_path(paths: Mapping[str, str], fragment: str) -> tuple[str, Path]:
    matches = [(name, Path(value)) for name, value in paths.items() if fragment in name]
    if len(matches) != 1:
        raise ProductionIntegrityError(
            f"workspace must define exactly one {fragment} path"
        )
    return matches[0]


def _safe_entries(directory: Path, scope: str) -> list[Path]:
    if directory.is_symlink() or not directory.is_dir():
        raise ProductionIntegrityError(f"{scope} path is missing or unsafe")
    return sorted(directory.iterdir(), key=lambda path: path.name)


def audit_production_estate(workspace_root: Path) -> dict[str, Any]:
    """Audit an existing workspace without creating, repairing or deleting files."""
    root = workspace_root.expanduser()
    try:
        workspace = load_production_workspace(root)
    except OperationsWorkspaceError as exc:
        raise ProductionIntegrityError(f"workspace is invalid: {exc}") from exc

    findings: list[dict[str, str]] = []
    candidate_count = revision_count = finalized_count = 0
    archive_count = verified_archive_count = 0
    paths = workspace["paths"]

    for name, value in sorted(paths.items()):
        path = Path(value)
        if path.is_symlink() or not path.is_dir():
            findings.append(_finding("UNSAFE_WORKSPACE_PATH", name, str(path)))

    try:
        candidate_name, candidate_root = _named_path(paths, "candidate")
        for entry in _safe_entries(candidate_root, candidate_name):
            if entry.is_symlink() or not entry.is_dir():
                findings.append(_finding(
                    "UNEXPECTED_CANDIDATE_ENTRY", entry.name,
                    "candidate entry must be a real directory",
                ))
                continue
            candidate_count += 1
            try:
                revisions = list_candidate_revisions(candidate_root, entry.name)
                if not revisions:
                    raise JournalCandidateStoreError("candidate has no revisions")
                revision_count += len(revisions)
                finalization = entry / "finalization"
                if finalization.exists() or finalization.is_symlink():
                    load_candidate_finalization(candidate_root, entry.name)
                    finalized_count += 1
            except (JournalCandidateStoreError, OSError) as exc:
                findings.append(_finding(
                    "INVALID_CANDIDATE", entry.name, str(exc),
                ))
    except (ProductionIntegrityError, OSError) as exc:
        findings.append(_finding("CANDIDATE_ESTATE_UNSAFE", "candidates", str(exc)))

    try:
        archive_name, archive_root = _named_path(paths, "archive")
        editions = archive_root / "editions"
        if editions.exists() or editions.is_symlink():
            for entry in _safe_entries(editions, archive_name):
                if entry.name.startswith(".archive-tmp-"):
                    findings.append(_finding(
                        "UNEXPECTED_ARCHIVE_ENTRY", entry.name,
                        "temporary archive entry remains",
                    ))
            listing = list_archived_editions(archive_root)
            archive_count = listing["edition_count"]
            for edition in listing["editions"]:
                try:
                    verify_archived_edition(archive_root, edition["journal_id"])
                    verified_archive_count += 1
                except (JournalArchiveStoreError, OSError) as exc:
                    findings.append(_finding(
                        "INVALID_ARCHIVE_EDITION", edition["journal_id"], str(exc),
                    ))
        elif any(archive_root.iterdir()):
            findings.append(_finding(
                "ARCHIVE_ESTATE_UNSAFE", archive_name,
                "archive root contains unexpected entries",
            ))
    except (ProductionIntegrityError, JournalArchiveStoreError, OSError) as exc:
        findings.append(_finding("ARCHIVE_ESTATE_UNSAFE", "archive", str(exc)))

    findings.sort(key=lambda item: (item["scope"], item["code"], item["message"]))
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "workspace_id": workspace["workspace_id"],
        "workspace_root": workspace["workspace_root"],
        "status": "PASS" if not findings else "FAIL",
        "counts": {
            "candidates": candidate_count,
            "candidate_revisions": revision_count,
            "finalized_candidates": finalized_count,
            "archived_editions": archive_count,
            "verified_archived_editions": verified_archive_count,
            "findings": len(findings),
        },
        "findings": findings,
        "provider_requests": 0,
        "wordpress_requests": 0,
        "tamil_rendered": False,
        "thirukkural_algorithm_usage": "TITLE_ONLY",
    }
    return validate_production_integrity_report(report)
