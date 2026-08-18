from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import FormatChecker, validate

from journal.archive import (
    JournalArchiveError,
    compute_archive_entry_sha256,
    create_archive_entry,
    validate_archive_entry,
)


VERIFICATION = {
    "journal_id": "LK-JOURNAL-2026-W34",
    "edition_date": "2026-08-23",
    "article_count": 2,
    "selected_case_ids": ["LK-0002", "LK-0001"],
    "manifest_sha256": "a" * 64,
    "assembly_sha256": "b" * 64,
    "pdf_sha256": "c" * 64,
    "renderer_version": "1.0.0",
    "verification_status": "VERIFIED",
}

COVERED_RANGE = {
    "start": "2026-08-17",
    "end": "2026-08-18",
}


def build_entry():
    return create_archive_entry(
        verification=VERIFICATION,
        covered_date_range=COVERED_RANGE,
        archived_at_utc="2026-08-18T14:00:00Z",
    )


def test_archive_entry_is_deterministic():
    first = build_entry()
    second = build_entry()

    assert first == second
    assert first["archive_entry_sha256"] == (
        compute_archive_entry_sha256(first)
    )


def test_archive_paths_are_canonical_and_relative():
    entry = build_entry()

    assert entry["paths"] == {
        "edition": (
            "editions/LK-JOURNAL-2026-W34/artifacts"
        ),
        "manifest": (
            "editions/LK-JOURNAL-2026-W34/"
            "artifacts/manifest.json"
        ),
        "assembly": (
            "editions/LK-JOURNAL-2026-W34/"
            "artifacts/assembly.json"
        ),
        "pdf": (
            "editions/LK-JOURNAL-2026-W34/"
            "artifacts/journal.pdf"
        ),
        "evidence": (
            "editions/LK-JOURNAL-2026-W34/"
            "artifacts/build-evidence.json"
        ),
    }


def test_unverified_edition_is_rejected():
    verification = {
        **VERIFICATION,
        "verification_status": "FAILED",
    }

    with pytest.raises(
        JournalArchiveError,
        match="must be VERIFIED",
    ):
        create_archive_entry(
            verification=verification,
            covered_date_range=COVERED_RANGE,
            archived_at_utc="2026-08-18T14:00:00Z",
        )


def test_duplicate_selected_case_ids_are_rejected():
    verification = {
        **VERIFICATION,
        "selected_case_ids": ["LK-0001", "LK-0001"],
    }

    with pytest.raises(
        JournalArchiveError,
        match="must be unique",
    ):
        create_archive_entry(
            verification=verification,
            covered_date_range=COVERED_RANGE,
            archived_at_utc="2026-08-18T14:00:00Z",
        )


def test_invalid_covered_range_is_rejected():
    with pytest.raises(
        JournalArchiveError,
        match="start cannot follow end",
    ):
        create_archive_entry(
            verification=VERIFICATION,
            covered_date_range={
                "start": "2026-08-19",
                "end": "2026-08-18",
            },
            archived_at_utc="2026-08-18T14:00:00Z",
        )


def test_tampered_archive_entry_is_rejected():
    entry = deepcopy(build_entry())
    entry["edition_date"] = "2026-08-24"

    with pytest.raises(
        JournalArchiveError,
        match="archive_entry_sha256 does not match",
    ):
        validate_archive_entry(entry)


def test_archive_entry_matches_json_schema():
    schema_path = (
        Path(__file__).parents[1]
        / "schemas"
        / "weekly_journal_archive_entry.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    validate(
        instance=build_entry(),
        schema=schema,
        format_checker=FormatChecker(),
    )
