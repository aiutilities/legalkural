import json
from pathlib import Path

import pytest

from journal.candidate import create_candidate_revision
from journal.candidate_store import (
    load_candidate_finalization,
    store_candidate_revision,
)
from journal.discovery import discover_articles, select_articles
from journal.finalization import finalize_candidate
from journal.workflow import (
    JournalWorkflowError,
    build_finalized_candidate_journal,
    verify_journal_edition,
)
from test_journal_workflow import create_eligible_case


CANDIDATE_ID = "LK-CANDIDATE-2026-W34"


def finalize_synthetic_candidate(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    discovery = discover_articles(tmp_path / "generated")
    selected = select_articles(discovery, ["LK-0001"])

    candidate = create_candidate_revision(
        candidate_id=CANDIDATE_ID,
        journal_id="LK-JOURNAL-2026-W34",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal",
        editor="Founder",
        revised_at_utc="2026-08-18T13:00:00Z",
        articles=selected,
    )
    candidate_root = tmp_path / "candidates"
    store_candidate_revision(candidate_root, candidate)
    finalize_candidate(
        storage_root=candidate_root,
        generated_root=tmp_path / "generated",
        candidate_id=CANDIDATE_ID,
        selected_by="Founder",
        finalized_at_utc="2026-08-18T13:10:00Z",
    )
    return candidate_root, candidate


def test_build_reuses_exact_finalized_candidate_manifest(tmp_path):
    candidate_root, candidate = finalize_synthetic_candidate(tmp_path)
    finalized_manifest = load_candidate_finalization(
        candidate_root,
        CANDIDATE_ID,
    )

    result = build_finalized_candidate_journal(
        project_root=tmp_path,
        candidate_storage_root=candidate_root,
        output_root=tmp_path / "journals",
        candidate_id=CANDIDATE_ID,
    )
    output = Path(result["output_directory"])
    built_manifest = json.loads(
        (output / "manifest.json").read_text(encoding="utf-8")
    )

    assert built_manifest == finalized_manifest
    assert result["manifest_sha256"] == (
        finalized_manifest["manifest_sha256"]
    )
    assert result["candidate_id"] == CANDIDATE_ID
    assert result["candidate_revision_number"] == 1
    assert result["candidate_sha256"] == (
        candidate["candidate_sha256"]
    )


def test_candidate_built_edition_is_fully_verified(tmp_path):
    candidate_root, unused = finalize_synthetic_candidate(tmp_path)

    result = build_finalized_candidate_journal(
        project_root=tmp_path,
        candidate_storage_root=candidate_root,
        output_root=tmp_path / "journals",
        candidate_id=CANDIDATE_ID,
    )
    verified = verify_journal_edition(
        Path(result["output_directory"])
    )
    manifest = json.loads(
        (
            Path(result["output_directory"])
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )

    assert verified["verification_status"] == "VERIFIED"
    assert verified["provider_requests"] == 0
    assert verified["wordpress_requests"] == 0
    assert manifest["candidate_lineage"]["candidate_id"] == (
        CANDIDATE_ID
    )


def test_unfinalized_candidate_cannot_be_built(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    discovery = discover_articles(tmp_path / "generated")
    selected = select_articles(discovery, ["LK-0001"])
    candidate = create_candidate_revision(
        candidate_id=CANDIDATE_ID,
        journal_id="LK-JOURNAL-2026-W34",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal",
        editor="Founder",
        revised_at_utc="2026-08-18T13:00:00Z",
        articles=selected,
    )
    candidate_root = tmp_path / "candidates"
    store_candidate_revision(candidate_root, candidate)

    with pytest.raises(
        JournalWorkflowError,
        match="cannot load finalized candidate",
    ):
        build_finalized_candidate_journal(
            project_root=tmp_path,
            candidate_storage_root=candidate_root,
            output_root=tmp_path / "journals",
            candidate_id=CANDIDATE_ID,
        )


def test_source_tamper_after_finalization_blocks_build(tmp_path):
    candidate_root, unused = finalize_synthetic_candidate(tmp_path)
    payload_path = (
        tmp_path
        / "generated"
        / "LK-0001"
        / "output"
        / "11-publication"
        / "wordpress-final-draft-payload.json"
    )
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["content"] = "<p>Tampered after finalization.</p>"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="content hash mismatch"):
        build_finalized_candidate_journal(
            project_root=tmp_path,
            candidate_storage_root=candidate_root,
            output_root=tmp_path / "journals",
            candidate_id=CANDIDATE_ID,
        )
