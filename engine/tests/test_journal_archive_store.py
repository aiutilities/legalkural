import json
from pathlib import Path

import pytest

from journal.archive import compute_archive_entry_sha256
from journal.archive_store import (
    JournalArchiveStoreError,
    inspect_archive_entry,
    list_archived_editions,
    register_verified_edition,
    verify_archived_edition,
)
from test_journal_workflow import (
    build,
    create_eligible_case,
)


def build_edition(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    result = build(tmp_path)
    return Path(result["output_directory"])


def register(tmp_path):
    edition = build_edition(tmp_path)
    archive_root = tmp_path / "archive"
    result = register_verified_edition(
        archive_root=archive_root,
        edition_directory=edition,
        archived_at_utc="2026-08-18T14:30:00Z",
    )
    return archive_root, edition, result


def test_verified_edition_is_registered_atomically(tmp_path):
    archive_root, unused, result = register(tmp_path)

    assert result["archive_verification_status"] == "VERIFIED"
    assert result["journal_id"] == "LK-JOURNAL-2026-W34"
    assert sorted(
        path.name
        for path in (
            archive_root
            / "editions"
            / result["journal_id"]
            / "artifacts"
        ).iterdir()
    ) == [
        "assembly.json",
        "build-evidence.json",
        "journal.pdf",
        "manifest.json",
    ]


def test_archive_listing_and_inspection(tmp_path):
    archive_root, unused, registered = register(tmp_path)

    listing = list_archived_editions(archive_root)
    inspected = inspect_archive_entry(
        archive_root,
        registered["journal_id"],
    )

    assert listing["edition_count"] == 1
    assert listing["editions"][0]["journal_id"] == (
        registered["journal_id"]
    )
    assert inspected["archive_entry_sha256"] == (
        registered["archive_entry_sha256"]
    )


def test_duplicate_journal_id_is_rejected(tmp_path):
    archive_root, edition, unused = register(tmp_path)

    with pytest.raises(
        JournalArchiveStoreError,
        match="already archived",
    ):
        register_verified_edition(
            archive_root=archive_root,
            edition_directory=edition,
            archived_at_utc="2026-08-18T14:35:00Z",
        )


def test_tampered_source_edition_is_rejected(tmp_path):
    edition = build_edition(tmp_path)
    pdf_path = edition / "journal.pdf"
    pdf_path.write_bytes(pdf_path.read_bytes() + b"TAMPERED")

    with pytest.raises(
        JournalArchiveStoreError,
        match="source edition is not verified",
    ):
        register_verified_edition(
            archive_root=tmp_path / "archive",
            edition_directory=edition,
            archived_at_utc="2026-08-18T14:30:00Z",
        )

    target = (
        tmp_path
        / "archive"
        / "editions"
        / "LK-JOURNAL-2026-W34"
    )
    assert not target.exists()


def test_tampered_archived_pdf_is_rejected(tmp_path):
    archive_root, unused, registered = register(tmp_path)
    pdf_path = (
        archive_root
        / registered["paths"]["pdf"]
    )
    pdf_path.write_bytes(pdf_path.read_bytes() + b"TAMPERED")

    with pytest.raises(
        JournalArchiveStoreError,
        match="archived edition verification failed",
    ):
        verify_archived_edition(
            archive_root,
            registered["journal_id"],
        )


def test_noncanonical_archive_paths_are_rejected(tmp_path):
    archive_root, unused, registered = register(tmp_path)
    entry_path = (
        archive_root
        / "editions"
        / registered["journal_id"]
        / "archive-entry.json"
    )
    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    entry["paths"]["pdf"] = "../journal.pdf"
    entry["archive_entry_sha256"] = (
        compute_archive_entry_sha256(entry)
    )
    entry_path.write_text(json.dumps(entry), encoding="utf-8")

    with pytest.raises(
        JournalArchiveStoreError,
        match="archive entry is invalid",
    ):
        inspect_archive_entry(
            archive_root,
            registered["journal_id"],
        )


def test_archive_root_symlink_is_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    archive_link = tmp_path / "archive-link"
    archive_link.symlink_to(outside, target_is_directory=True)
    edition = build_edition(tmp_path)

    with pytest.raises(
        JournalArchiveStoreError,
        match="archive root cannot be a symlink",
    ):
        register_verified_edition(
            archive_root=archive_link,
            edition_directory=edition,
            archived_at_utc="2026-08-18T14:30:00Z",
        )
