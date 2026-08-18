"""Append-only local storage for journal candidate revisions."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .candidate import (
    JournalCandidateError,
    validate_candidate_revision,
)


REVISION_WIDTH = 6
REVISION_FILE = "candidate.json"


class JournalCandidateStoreError(ValueError):
    """Raised when candidate revision storage is invalid or unsafe."""


def _storage_root(storage_root: Path) -> Path:
    supplied = storage_root.expanduser()
    if supplied.exists() and supplied.is_symlink():
        raise JournalCandidateStoreError(
            "candidate storage root cannot be a symlink"
        )
    root = supplied.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise JournalCandidateStoreError(
            "candidate storage root must be a directory"
        )
    return root


def _candidate_directory(root: Path, candidate_id: str) -> Path:
    if (
        not isinstance(candidate_id, str)
        or not candidate_id
        or "/" in candidate_id
        or "\\" in candidate_id
        or candidate_id in {".", ".."}
    ):
        raise JournalCandidateStoreError("candidate_id path is invalid")

    candidate_directory = root / candidate_id
    if candidate_directory.exists() and candidate_directory.is_symlink():
        raise JournalCandidateStoreError(
            "candidate directory cannot be a symlink"
        )

    resolved_parent = candidate_directory.parent.resolve()
    if resolved_parent != root:
        raise JournalCandidateStoreError(
            "candidate directory escapes storage root"
        )
    return candidate_directory


def _revision_name(revision_number: int) -> str:
    if (
        not isinstance(revision_number, int)
        or isinstance(revision_number, bool)
        or revision_number < 1
    ):
        raise JournalCandidateStoreError(
            "revision_number must be positive"
        )
    return f"{revision_number:0{REVISION_WIDTH}d}"


def _revision_directories(revisions: Path) -> list[Path]:
    if not revisions.exists():
        return []
    if revisions.is_symlink() or not revisions.is_dir():
        raise JournalCandidateStoreError(
            "revisions path must be a real directory"
        )

    result: list[Path] = []
    for entry in revisions.iterdir():
        if entry.name.startswith(".candidate-tmp-"):
            continue
        if (
            entry.is_symlink()
            or not entry.is_dir()
            or len(entry.name) != REVISION_WIDTH
            or not entry.name.isdigit()
            or int(entry.name) < 1
        ):
            raise JournalCandidateStoreError(
                f"unexpected candidate storage entry: {entry.name}"
            )
        result.append(entry)

    result.sort(key=lambda item: int(item.name))
    expected = list(range(1, len(result) + 1))
    actual = [int(item.name) for item in result]
    if actual != expected:
        raise JournalCandidateStoreError(
            "candidate revision sequence is not contiguous"
        )
    return result


def _load_revision_file(
    path: Path,
    *,
    candidate_id: str,
    revision_number: int,
) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise JournalCandidateStoreError(
            "candidate revision file is missing or unsafe"
        )

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise JournalCandidateStoreError(
            "candidate revision JSON is invalid"
        ) from exc

    try:
        validate_candidate_revision(value)
    except JournalCandidateError as exc:
        raise JournalCandidateStoreError(
            f"stored candidate revision is invalid: {exc}"
        ) from exc

    if value["candidate_id"] != candidate_id:
        raise JournalCandidateStoreError(
            "stored candidate identity does not match its path"
        )
    if value["revision_number"] != revision_number:
        raise JournalCandidateStoreError(
            "stored revision number does not match its path"
        )
    return value


def list_candidate_revisions(
    storage_root: Path,
    candidate_id: str,
) -> list[dict[str, Any]]:
    """List and verify all stored revisions in append-only order."""

    root = _storage_root(storage_root)
    candidate_directory = _candidate_directory(root, candidate_id)
    if not candidate_directory.exists():
        return []
    if not candidate_directory.is_dir():
        raise JournalCandidateStoreError(
            "candidate path must be a directory"
        )

    revision_directories = _revision_directories(
        candidate_directory / "revisions"
    )
    result: list[dict[str, Any]] = []
    previous_sha256: str | None = None

    for directory in revision_directories:
        revision_number = int(directory.name)
        entries = list(directory.iterdir())
        if (
            len(entries) != 1
            or entries[0].name != REVISION_FILE
        ):
            raise JournalCandidateStoreError(
                "candidate revision directory is incomplete"
            )

        candidate = _load_revision_file(
            directory / REVISION_FILE,
            candidate_id=candidate_id,
            revision_number=revision_number,
        )

        if revision_number == 1:
            if candidate["previous_revision_sha256"] is not None:
                raise JournalCandidateStoreError(
                    "first stored revision has invalid lineage"
                )
        elif candidate["previous_revision_sha256"] != previous_sha256:
            raise JournalCandidateStoreError(
                "stored candidate revision hash chain is broken"
            )

        previous_sha256 = candidate["candidate_sha256"]
        result.append(candidate)

    return result


def load_candidate_revision(
    storage_root: Path,
    candidate_id: str,
    revision_number: int | None = None,
) -> dict[str, Any]:
    """Load a specific revision, or the latest revision when omitted."""

    revisions = list_candidate_revisions(storage_root, candidate_id)
    if not revisions:
        raise JournalCandidateStoreError(
            f"candidate does not exist: {candidate_id}"
        )

    if revision_number is None:
        return deepcopy(revisions[-1])

    _revision_name(revision_number)
    if revision_number > len(revisions):
        raise JournalCandidateStoreError(
            f"candidate revision does not exist: {revision_number}"
        )
    return deepcopy(revisions[revision_number - 1])


def store_candidate_revision(
    storage_root: Path,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Atomically append one validated candidate revision."""

    try:
        validate_candidate_revision(candidate)
    except JournalCandidateError as exc:
        raise JournalCandidateStoreError(
            f"candidate revision is invalid: {exc}"
        ) from exc

    value = deepcopy(dict(candidate))
    root = _storage_root(storage_root)
    candidate_directory = _candidate_directory(
        root,
        value["candidate_id"],
    )
    revisions_directory = candidate_directory / "revisions"

    if candidate_directory.exists() and not candidate_directory.is_dir():
        raise JournalCandidateStoreError(
            "candidate path must be a directory"
        )

    candidate_directory.mkdir(exist_ok=True)
    if revisions_directory.exists() and revisions_directory.is_symlink():
        raise JournalCandidateStoreError(
            "revisions directory cannot be a symlink"
        )
    revisions_directory.mkdir(exist_ok=True)

    existing = list_candidate_revisions(
        root,
        value["candidate_id"],
    )
    expected_revision = len(existing) + 1

    if value["revision_number"] != expected_revision:
        raise JournalCandidateStoreError(
            f"next revision must be {expected_revision}"
        )

    if existing:
        previous = existing[-1]
        if (
            value["previous_revision_sha256"]
            != previous["candidate_sha256"]
        ):
            raise JournalCandidateStoreError(
                "new revision does not extend the stored hash chain"
            )
        for field in (
            "candidate_id",
            "journal_id",
            "edition_date",
            "title",
            "editor",
            "created_at_utc",
        ):
            if value[field] != previous[field]:
                raise JournalCandidateStoreError(
                    f"immutable candidate field changed: {field}"
                )

    target = revisions_directory / _revision_name(
        value["revision_number"]
    )
    if target.exists():
        raise JournalCandidateStoreError(
            "candidate revision already exists"
        )

    temporary = Path(
        tempfile.mkdtemp(
            prefix=".candidate-tmp-",
            dir=revisions_directory,
        )
    )

    try:
        output = temporary / REVISION_FILE
        payload = (
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        with output.open("x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        os.rename(temporary, target)

        directory_descriptor = os.open(
            revisions_directory,
            os.O_RDONLY,
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    stored = load_candidate_revision(
        root,
        value["candidate_id"],
        value["revision_number"],
    )
    return {
        "candidate_id": stored["candidate_id"],
        "revision_number": stored["revision_number"],
        "candidate_sha256": stored["candidate_sha256"],
        "revision_file": (
            target.relative_to(root) / REVISION_FILE
        ).as_posix(),
        "status": "STORED",
    }
