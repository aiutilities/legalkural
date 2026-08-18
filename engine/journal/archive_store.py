"""Atomic local storage for verified LegalKural journal editions."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .archive import (
    JOURNAL_ID_PATTERN,
    JournalArchiveError,
    create_archive_entry,
    validate_archive_entry,
)
from .manifest import canonical_json_bytes
from .workflow import (
    JournalWorkflowError,
    verify_journal_edition,
)


ARCHIVE_ENTRY_FILE = "archive-entry.json"
ARTIFACT_DIRECTORY = "artifacts"
ARTIFACT_NAMES = {
    "manifest.json",
    "assembly.json",
    "journal.pdf",
    "build-evidence.json",
}


class JournalArchiveStoreError(ValueError):
    """Raised when archive storage is incomplete, unsafe, or invalid."""


def _archive_root(archive_root: Path) -> Path:
    supplied = archive_root.expanduser()
    if supplied.exists() and supplied.is_symlink():
        raise JournalArchiveStoreError(
            "archive root cannot be a symlink"
        )

    root = supplied.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise JournalArchiveStoreError(
            "archive root must be a directory"
        )
    return root


def _editions_directory(root: Path) -> Path:
    editions = root / "editions"
    if editions.exists() and editions.is_symlink():
        raise JournalArchiveStoreError(
            "archive editions directory cannot be a symlink"
        )
    editions.mkdir(exist_ok=True)
    if not editions.is_dir():
        raise JournalArchiveStoreError(
            "archive editions path must be a directory"
        )
    return editions


def _journal_directory(root: Path, journal_id: str) -> Path:
    if (
        not isinstance(journal_id, str)
        or not JOURNAL_ID_PATTERN.fullmatch(journal_id)
    ):
        raise JournalArchiveStoreError("journal_id is invalid")

    editions = _editions_directory(root)
    target = editions / journal_id
    if target.exists() and target.is_symlink():
        raise JournalArchiveStoreError(
            "archived journal directory cannot be a symlink"
        )
    if target.parent.resolve() != editions.resolve():
        raise JournalArchiveStoreError(
            "archived journal path escapes archive root"
        )
    return target


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise JournalArchiveStoreError(
            f"{label} must be a regular file"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JournalArchiveStoreError(
            f"{label} is not valid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise JournalArchiveStoreError(
            f"{label} must contain an object"
        )
    return value


def _write_bytes_fsynced(path: Path, value: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def inspect_archive_entry(
    archive_root: Path,
    journal_id: str,
) -> dict[str, Any]:
    """Load and validate one immutable archive entry."""

    root = _archive_root(archive_root)
    target = _journal_directory(root, journal_id)
    if not target.exists():
        raise JournalArchiveStoreError(
            f"archived journal does not exist: {journal_id}"
        )
    if target.is_symlink() or not target.is_dir():
        raise JournalArchiveStoreError(
            "archived journal path is unsafe"
        )

    if {path.name for path in target.iterdir()} != {
        ARCHIVE_ENTRY_FILE,
        ARTIFACT_DIRECTORY,
    }:
        raise JournalArchiveStoreError(
            "archived journal directory is incomplete"
        )

    artifacts = target / ARTIFACT_DIRECTORY
    if artifacts.is_symlink() or not artifacts.is_dir():
        raise JournalArchiveStoreError(
            "archived artifact directory is unsafe"
        )

    entry_path = target / ARCHIVE_ENTRY_FILE
    entry = _read_json(entry_path, "archive entry")
    try:
        validate_archive_entry(entry)
    except JournalArchiveError as exc:
        raise JournalArchiveStoreError(
            f"archive entry is invalid: {exc}"
        ) from exc

    if entry["journal_id"] != journal_id:
        raise JournalArchiveStoreError(
            "archive entry identity does not match its path"
        )

    expected_entry = (
        f"editions/{journal_id}/{ARCHIVE_ENTRY_FILE}"
    )
    if entry_path.relative_to(root).as_posix() != expected_entry:
        raise JournalArchiveStoreError(
            "archive entry path is not canonical"
        )

    return entry


def verify_archived_edition(
    archive_root: Path,
    journal_id: str,
) -> dict[str, Any]:
    """Reverify an archived edition and all archive metadata."""

    root = _archive_root(archive_root)
    entry = inspect_archive_entry(root, journal_id)
    artifacts = (
        root
        / "editions"
        / journal_id
        / ARTIFACT_DIRECTORY
    )

    try:
        verification = verify_journal_edition(artifacts)
    except JournalWorkflowError as exc:
        raise JournalArchiveStoreError(
            f"archived edition verification failed: {exc}"
        ) from exc

    manifest = _read_json(
        artifacts / "manifest.json",
        "archived manifest",
    )

    comparisons = {
        "journal_id": verification["journal_id"],
        "edition_date": verification["edition_date"],
        "article_count": verification["article_count"],
        "selected_case_ids": verification["selected_case_ids"],
        "manifest_sha256": verification["manifest_sha256"],
        "assembly_sha256": verification["assembly_sha256"],
        "pdf_sha256": verification["pdf_sha256"],
        "renderer_version": verification["renderer_version"],
        "verification_status": verification[
            "verification_status"
        ],
        "covered_date_range": manifest["covered_date_range"],
    }
    for field, actual in comparisons.items():
        if entry[field] != actual:
            raise JournalArchiveStoreError(
                f"archive {field} does not match archived edition"
            )

    result = deepcopy(entry)
    result["archive_verification_status"] = "VERIFIED"
    result["archive_directory"] = (
        root / "editions" / journal_id
    ).as_posix()
    return result


def list_archived_editions(
    archive_root: Path,
) -> dict[str, Any]:
    """List all valid archive entries in journal-ID order."""

    root = _archive_root(archive_root)
    editions = _editions_directory(root)
    journal_ids: list[str] = []

    for path in editions.iterdir():
        if path.name.startswith(".archive-tmp-"):
            continue
        if (
            path.is_symlink()
            or not path.is_dir()
            or not JOURNAL_ID_PATTERN.fullmatch(path.name)
        ):
            raise JournalArchiveStoreError(
                f"unexpected archive entry: {path.name}"
            )
        journal_ids.append(path.name)

    entries = [
        inspect_archive_entry(root, journal_id)
        for journal_id in sorted(journal_ids)
    ]
    return {
        "schema_version": "1.0",
        "archive_root": root.as_posix(),
        "edition_count": len(entries),
        "editions": [
            {
                "journal_id": entry["journal_id"],
                "edition_date": entry["edition_date"],
                "article_count": entry["article_count"],
                "selected_case_ids": entry[
                    "selected_case_ids"
                ],
                "renderer_version": entry["renderer_version"],
                "verification_status": entry[
                    "verification_status"
                ],
                "archived_at_utc": entry["archived_at_utc"],
                "archive_entry_sha256": entry[
                    "archive_entry_sha256"
                ],
            }
            for entry in entries
        ],
    }


def register_verified_edition(
    *,
    archive_root: Path,
    edition_directory: Path,
    archived_at_utc: str,
) -> dict[str, Any]:
    """Atomically register one complete, verified journal edition."""

    supplied_edition = edition_directory.expanduser()
    if supplied_edition.is_symlink():
        raise JournalArchiveStoreError(
            "source edition directory cannot be a symlink"
        )

    source = supplied_edition.resolve()
    try:
        verification = verify_journal_edition(source)
    except JournalWorkflowError as exc:
        raise JournalArchiveStoreError(
            f"source edition is not verified: {exc}"
        ) from exc

    manifest = _read_json(
        source / "manifest.json",
        "source manifest",
    )
    entry = create_archive_entry(
        verification=verification,
        covered_date_range=manifest["covered_date_range"],
        archived_at_utc=archived_at_utc,
    )

    root = _archive_root(archive_root)
    editions = _editions_directory(root)
    target = _journal_directory(root, entry["journal_id"])
    if target.exists():
        raise JournalArchiveStoreError(
            f"journal_id is already archived: {entry['journal_id']}"
        )

    temporary = Path(
        tempfile.mkdtemp(
            prefix=".archive-tmp-",
            dir=editions,
        )
    )
    try:
        artifacts = temporary / ARTIFACT_DIRECTORY
        artifacts.mkdir()

        for name in sorted(ARTIFACT_NAMES):
            source_path = source / name
            destination = artifacts / name
            _write_bytes_fsynced(
                destination,
                source_path.read_bytes(),
            )

        copied_verification = verify_journal_edition(artifacts)
        for field in (
            "journal_id",
            "edition_date",
            "manifest_sha256",
            "assembly_sha256",
            "pdf_sha256",
            "renderer_version",
        ):
            if copied_verification[field] != verification[field]:
                raise JournalArchiveStoreError(
                    f"copied edition {field} changed"
                )

        _write_bytes_fsynced(
            temporary / ARCHIVE_ENTRY_FILE,
            canonical_json_bytes(entry) + b"\n",
        )

        os.rename(temporary, target)

        directory_descriptor = os.open(editions, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return verify_archived_edition(root, entry["journal_id"])
