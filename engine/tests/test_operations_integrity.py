from __future__ import annotations

import json
from pathlib import Path

import pytest

from operations.integrity import (
    ProductionIntegrityError,
    audit_production_estate,
    validate_production_integrity_report,
)
from operations.workspace import initialize_production_workspace


def _workspace(tmp_path: Path) -> tuple[Path, dict]:
    root = tmp_path / "production"
    return root, initialize_production_workspace(root, "LK-PRODUCTION-TEST")


def _snapshot(root: Path) -> list[tuple[str, str, bytes | None]]:
    result = []
    for path in sorted(root.rglob("*")):
        kind = "link" if path.is_symlink() else "dir" if path.is_dir() else "file"
        result.append((path.relative_to(root).as_posix(), kind, path.read_bytes() if path.is_file() else None))
    return result


def test_clean_empty_workspace_passes(tmp_path):
    root, _ = _workspace(tmp_path)
    report = audit_production_estate(root)
    assert report["status"] == "PASS"
    assert report["counts"]["findings"] == 0


def test_audit_is_content_read_only(tmp_path):
    root, _ = _workspace(tmp_path)
    before = _snapshot(root)
    audit_production_estate(root)
    assert _snapshot(root) == before


def test_missing_workspace_is_rejected_without_creation(tmp_path):
    root = tmp_path / "missing"
    with pytest.raises(ProductionIntegrityError, match="workspace is invalid"):
        audit_production_estate(root)
    assert not root.exists()


def test_tampered_workspace_manifest_is_rejected(tmp_path):
    root, _ = _workspace(tmp_path)
    manifest = root / "workspace.json"
    payload = json.loads(manifest.read_text())
    payload["unexpected"] = True
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ProductionIntegrityError, match="workspace is invalid"):
        audit_production_estate(root)


def test_unexpected_candidate_file_fails(tmp_path):
    root, workspace = _workspace(tmp_path)
    candidates = Path(next(v for k, v in workspace["paths"].items() if "candidate" in k))
    (candidates / "unsafe.txt").write_text("unsafe")
    report = audit_production_estate(root)
    assert report["status"] == "FAIL"
    assert report["findings"][0]["code"] == "UNEXPECTED_CANDIDATE_ENTRY"


def test_candidate_symlink_fails(tmp_path):
    root, workspace = _workspace(tmp_path)
    candidates = Path(next(v for k, v in workspace["paths"].items() if "candidate" in k))
    outside = tmp_path / "outside"
    outside.mkdir()
    (candidates / "LK-CANDIDATE-UNSAFE").symlink_to(outside, target_is_directory=True)
    report = audit_production_estate(root)
    assert report["status"] == "FAIL"


def test_empty_candidate_directory_fails(tmp_path):
    root, workspace = _workspace(tmp_path)
    candidates = Path(next(v for k, v in workspace["paths"].items() if "candidate" in k))
    (candidates / "LK-CANDIDATE-EMPTY").mkdir()
    report = audit_production_estate(root)
    assert report["status"] == "FAIL"
    assert report["counts"]["candidates"] == 1


def test_stale_archive_temporary_entry_fails(tmp_path):
    root, workspace = _workspace(tmp_path)
    archive = Path(next(v for k, v in workspace["paths"].items() if "archive" in k))
    editions = archive / "editions"
    editions.mkdir()
    (editions / ".archive-tmp-stale").mkdir()
    report = audit_production_estate(root)
    assert report["status"] == "FAIL"


def test_report_preserves_project_language_contract(tmp_path):
    root, _ = _workspace(tmp_path)
    report = audit_production_estate(root)
    assert report["tamil_rendered"] is False
    assert report["thirukkural_algorithm_usage"] == "TITLE_ONLY"


def test_report_records_zero_external_requests(tmp_path):
    root, _ = _workspace(tmp_path)
    report = audit_production_estate(root)
    assert report["provider_requests"] == 0
    assert report["wordpress_requests"] == 0


def test_report_schema_rejects_extra_field(tmp_path):
    root, _ = _workspace(tmp_path)
    report = audit_production_estate(root)
    report["unexpected"] = True
    with pytest.raises(ProductionIntegrityError, match="integrity report is invalid"):
        validate_production_integrity_report(report)


def test_valid_candidate_and_archive_estate_passes(tmp_path, monkeypatch):
    root, workspace = _workspace(tmp_path)
    candidates = Path(
        next(v for k, v in workspace["paths"].items() if "candidate" in k)
    )
    candidate = candidates / "LK-CANDIDATE-VALID"
    candidate.mkdir()
    (candidate / "finalization").mkdir()

    archive = Path(
        next(v for k, v in workspace["paths"].items() if "archive" in k)
    )
    editions = archive / "editions"
    editions.mkdir()
    (editions / "LK-JOURNAL-2026-W34-VALID").mkdir()

    monkeypatch.setattr(
        "operations.integrity.list_candidate_revisions",
        lambda storage_root, candidate_id: [
            {"candidate_id": candidate_id, "revision_number": 1}
        ],
    )
    monkeypatch.setattr(
        "operations.integrity.load_candidate_finalization",
        lambda storage_root, candidate_id: {
            "candidate_lineage": {"candidate_id": candidate_id}
        },
    )
    monkeypatch.setattr(
        "operations.integrity.list_archived_editions",
        lambda archive_root: {
            "edition_count": 1,
            "editions": [
                {"journal_id": "LK-JOURNAL-2026-W34-VALID"}
            ],
        },
    )
    monkeypatch.setattr(
        "operations.integrity.verify_archived_edition",
        lambda archive_root, journal_id: {
            "journal_id": journal_id,
            "archive_verification_status": "VERIFIED",
        },
    )

    report = audit_production_estate(root)

    assert report["status"] == "PASS"
    assert report["counts"] == {
        "candidates": 1,
        "candidate_revisions": 1,
        "finalized_candidates": 1,
        "archived_editions": 1,
        "verified_archived_editions": 1,
        "findings": 0,
    }


def test_tampered_candidate_revision_fails_audit(tmp_path, monkeypatch):
    from journal.candidate_store import JournalCandidateStoreError

    root, workspace = _workspace(tmp_path)
    candidates = Path(
        next(v for k, v in workspace["paths"].items() if "candidate" in k)
    )
    (candidates / "LK-CANDIDATE-TAMPERED").mkdir()

    def reject_tamper(storage_root, candidate_id):
        raise JournalCandidateStoreError("candidate sha256 does not match")

    monkeypatch.setattr(
        "operations.integrity.list_candidate_revisions",
        reject_tamper,
    )

    report = audit_production_estate(root)

    assert report["status"] == "FAIL"
    assert report["findings"][0]["code"] == "INVALID_CANDIDATE"
    assert "sha256" in report["findings"][0]["message"]


def test_broken_candidate_revision_lineage_fails_audit(
    tmp_path,
    monkeypatch,
):
    from journal.candidate_store import JournalCandidateStoreError

    root, workspace = _workspace(tmp_path)
    candidates = Path(
        next(v for k, v in workspace["paths"].items() if "candidate" in k)
    )
    (candidates / "LK-CANDIDATE-BROKEN").mkdir()

    def reject_lineage(storage_root, candidate_id):
        raise JournalCandidateStoreError(
            "stored candidate revision hash chain is broken"
        )

    monkeypatch.setattr(
        "operations.integrity.list_candidate_revisions",
        reject_lineage,
    )

    report = audit_production_estate(root)

    assert report["status"] == "FAIL"
    assert report["findings"][0]["code"] == "INVALID_CANDIDATE"
    assert "hash chain is broken" in report["findings"][0]["message"]


def test_tampered_archived_artifact_fails_audit(tmp_path, monkeypatch):
    from journal.archive_store import JournalArchiveStoreError

    root, workspace = _workspace(tmp_path)
    archive = Path(
        next(v for k, v in workspace["paths"].items() if "archive" in k)
    )
    editions = archive / "editions"
    editions.mkdir()
    journal_id = "LK-JOURNAL-2026-W34-TAMPERED"
    (editions / journal_id).mkdir()

    monkeypatch.setattr(
        "operations.integrity.list_archived_editions",
        lambda archive_root: {
            "edition_count": 1,
            "editions": [{"journal_id": journal_id}],
        },
    )

    def reject_artifact(archive_root, supplied_journal_id):
        raise JournalArchiveStoreError(
            "archived edition verification failed: pdf sha256 mismatch"
        )

    monkeypatch.setattr(
        "operations.integrity.verify_archived_edition",
        reject_artifact,
    )

    report = audit_production_estate(root)

    assert report["status"] == "FAIL"
    assert report["findings"][0]["code"] == "INVALID_ARCHIVE_EDITION"
    assert "pdf sha256 mismatch" in report["findings"][0]["message"]
