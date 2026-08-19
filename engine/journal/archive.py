"""Immutable contracts for the local LegalKural journal archive."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime
import hashlib
from pathlib import PurePosixPath
import re
from typing import Any

from .manifest import canonical_json_bytes


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
JOURNAL_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]+$")

ARCHIVE_ENTRY_KEYS = {
    "schema_version",
    "journal_id",
    "edition_date",
    "covered_date_range",
    "article_count",
    "selected_case_ids",
    "manifest_sha256",
    "assembly_sha256",
    "pdf_sha256",
    "renderer_version",
    "verification_status",
    "archived_at_utc",
    "paths",
    "archive_entry_sha256",
}

PATH_KEYS = {
    "edition",
    "manifest",
    "assembly",
    "pdf",
    "evidence",
}


class JournalArchiveError(ValueError):
    """Raised when an archive entry is invalid."""


def compute_archive_entry_sha256(
    entry: Mapping[str, Any],
) -> str:
    payload = deepcopy(dict(entry))
    payload.pop("archive_entry_sha256", None)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JournalArchiveError(f"{field} must be non-empty text")
    return value.strip()


def _journal_id(value: Any) -> str:
    normalized = _text(value, "journal_id")
    if not JOURNAL_ID_PATTERN.fullmatch(normalized):
        raise JournalArchiveError("journal_id is invalid")
    return normalized


def _date(value: Any, field: str) -> str:
    normalized = _text(value, field)
    try:
        date.fromisoformat(normalized)
    except ValueError as exc:
        raise JournalArchiveError(
            f"{field} must use YYYY-MM-DD format"
        ) from exc
    return normalized


def _utc(value: Any, field: str) -> str:
    normalized = _text(value, field)
    if not normalized.endswith("Z"):
        raise JournalArchiveError(f"{field} must be explicit UTC")
    try:
        parsed = datetime.fromisoformat(
            normalized[:-1] + "+00:00"
        )
    except ValueError as exc:
        raise JournalArchiveError(
            f"{field} must use ISO-8601 UTC format"
        ) from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise JournalArchiveError(f"{field} must be UTC")
    return normalized


def _sha256(value: Any, field: str) -> str:
    normalized = _text(value, field)
    if not SHA256_PATTERN.fullmatch(normalized):
        raise JournalArchiveError(
            f"{field} must be a SHA-256 digest"
        )
    return normalized


def _covered_range(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"start", "end"}:
        raise JournalArchiveError(
            "covered_date_range fields are invalid"
        )
    start = _date(value.get("start"), "covered_date_range.start")
    end = _date(value.get("end"), "covered_date_range.end")
    if start > end:
        raise JournalArchiveError(
            "covered_date_range start cannot follow end"
        )
    return {"start": start, "end": end}


def _case_ids(value: Any) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(
            not isinstance(item, str) or not item.strip()
            for item in value
        )
    ):
        raise JournalArchiveError(
            "selected_case_ids must be a non-empty string list"
        )

    normalized = [item.strip() for item in value]
    if len(normalized) != len(set(normalized)):
        raise JournalArchiveError(
            "selected_case_ids must be unique"
        )
    return normalized


def _expected_paths(journal_id: str) -> dict[str, str]:
    edition = f"editions/{journal_id}/artifacts"
    return {
        "edition": edition,
        "manifest": f"{edition}/manifest.json",
        "assembly": f"{edition}/assembly.json",
        "pdf": f"{edition}/journal.pdf",
        "evidence": f"{edition}/build-evidence.json",
    }


def _paths(value: Any, journal_id: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != PATH_KEYS:
        raise JournalArchiveError("archive paths are invalid")

    normalized: dict[str, str] = {}
    for field in sorted(PATH_KEYS):
        path_text = _text(value.get(field), f"paths.{field}")
        path = PurePosixPath(path_text)
        if path.is_absolute() or ".." in path.parts:
            raise JournalArchiveError(
                f"paths.{field} must be a safe relative path"
            )
        if path.as_posix() != path_text:
            raise JournalArchiveError(
                f"paths.{field} must be canonical"
            )
        normalized[field] = path_text

    expected = _expected_paths(journal_id)
    if normalized != expected:
        raise JournalArchiveError(
            "archive paths do not match canonical journal paths"
        )
    return expected


def create_archive_entry(
    *,
    verification: Mapping[str, Any],
    covered_date_range: Mapping[str, Any],
    archived_at_utc: str,
) -> dict[str, Any]:
    """Create a deterministic archive entry from verified evidence."""

    if not isinstance(verification, Mapping):
        raise JournalArchiveError(
            "verification result must be an object"
        )
    if verification.get("verification_status") != "VERIFIED":
        raise JournalArchiveError(
            "journal edition must be VERIFIED before archival"
        )

    journal_id = _journal_id(verification.get("journal_id"))
    selected_case_ids = _case_ids(
        verification.get("selected_case_ids")
    )
    article_count = verification.get("article_count")
    if (
        not isinstance(article_count, int)
        or isinstance(article_count, bool)
        or article_count < 1
        or article_count != len(selected_case_ids)
    ):
        raise JournalArchiveError(
            "article_count does not match selected_case_ids"
        )

    entry: dict[str, Any] = {
        "schema_version": "1.0",
        "journal_id": journal_id,
        "edition_date": _date(
            verification.get("edition_date"),
            "edition_date",
        ),
        "covered_date_range": _covered_range(
            covered_date_range
        ),
        "article_count": article_count,
        "selected_case_ids": selected_case_ids,
        "manifest_sha256": _sha256(
            verification.get("manifest_sha256"),
            "manifest_sha256",
        ),
        "assembly_sha256": _sha256(
            verification.get("assembly_sha256"),
            "assembly_sha256",
        ),
        "pdf_sha256": _sha256(
            verification.get("pdf_sha256"),
            "pdf_sha256",
        ),
        "renderer_version": _text(
            verification.get("renderer_version"),
            "renderer_version",
        ),
        "verification_status": "VERIFIED",
        "archived_at_utc": _utc(
            archived_at_utc,
            "archived_at_utc",
        ),
        "paths": _expected_paths(journal_id),
    }
    entry["archive_entry_sha256"] = (
        compute_archive_entry_sha256(entry)
    )
    validate_archive_entry(entry)
    return entry


def validate_archive_entry(entry: Mapping[str, Any]) -> None:
    """Validate archive structure, canonical paths, and digest."""

    if not isinstance(entry, Mapping):
        raise JournalArchiveError("archive entry must be an object")
    if set(entry) != ARCHIVE_ENTRY_KEYS:
        raise JournalArchiveError(
            "archive entry fields do not match the contract"
        )
    if entry.get("schema_version") != "1.0":
        raise JournalArchiveError(
            "unsupported archive schema_version"
        )

    journal_id = _journal_id(entry.get("journal_id"))
    _date(entry.get("edition_date"), "edition_date")
    _covered_range(entry.get("covered_date_range"))
    case_ids = _case_ids(entry.get("selected_case_ids"))

    article_count = entry.get("article_count")
    if (
        not isinstance(article_count, int)
        or isinstance(article_count, bool)
        or article_count < 1
        or article_count != len(case_ids)
    ):
        raise JournalArchiveError(
            "article_count does not match selected_case_ids"
        )

    for field in (
        "manifest_sha256",
        "assembly_sha256",
        "pdf_sha256",
    ):
        _sha256(entry.get(field), field)

    if entry.get("renderer_version") not in {"1.0.0", "2.0.0"}:
        raise JournalArchiveError(
            "unsupported renderer_version"
        )
    if entry.get("verification_status") != "VERIFIED":
        raise JournalArchiveError(
            "archive verification_status must be VERIFIED"
        )

    _utc(entry.get("archived_at_utc"), "archived_at_utc")
    _paths(entry.get("paths"), journal_id)

    supplied = _sha256(
        entry.get("archive_entry_sha256"),
        "archive_entry_sha256",
    )
    expected = compute_archive_entry_sha256(entry)
    if supplied != expected:
        raise JournalArchiveError(
            "archive_entry_sha256 does not match content"
        )
