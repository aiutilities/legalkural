import json

import pytest

import journal.finalization as finalization
from journal.candidate import (
    create_candidate_revision,
    revise_candidate,
)
from journal.candidate_store import (
    JournalCandidateStoreError,
    load_candidate_finalization,
    store_candidate_revision,
)
from journal.finalization import (
    JournalCandidateFinalizationError,
    finalize_candidate,
)


ARTICLE = {
    "eligible": True,
    "case_id": "LK-0001",
    "title": "First Certified Article",
    "slug": "first-certified-article",
    "source_payload": "generated/LK-0001/payload.json",
    "content_sha256": "a" * 64,
    "publication_evidence": "generated/LK-0001/evidence.json",
    "publication_evidence_sha256": "b" * 64,
    "post_id": 101,
    "published_url": "https://example.test/first/",
    "published_at": "2026-08-17T10:00:00",
    "author": 201,
    "categories": [301],
    "tags": [401, 402],
}


def discovery(article=ARTICLE):
    return {
        "schema_version": "1.0",
        "generated_root": "/generated",
        "eligible": [article],
        "rejected": [],
    }


def stored_candidate(tmp_path):
    candidate = create_candidate_revision(
        candidate_id="LK-CANDIDATE-2026-W34",
        journal_id="LK-JOURNAL-2026-W34",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal",
        editor="Founder",
        revised_at_utc="2026-08-18T13:00:00Z",
        articles=[ARTICLE],
    )
    store_candidate_revision(tmp_path, candidate)
    return candidate


def finalize(tmp_path, monkeypatch, report=None):
    monkeypatch.setattr(
        finalization,
        "discover_articles",
        lambda unused: report or discovery(),
    )
    return finalize_candidate(
        storage_root=tmp_path,
        generated_root=tmp_path / "generated",
        candidate_id="LK-CANDIDATE-2026-W34",
        selected_by="Founder",
        finalized_at_utc="2026-08-18T13:10:00Z",
    )


def test_latest_candidate_is_deliberately_finalized(
    tmp_path,
    monkeypatch,
):
    candidate = stored_candidate(tmp_path)

    result = finalize(tmp_path, monkeypatch)
    manifest = load_candidate_finalization(
        tmp_path,
        candidate["candidate_id"],
    )

    assert result["status"] == "FINALIZED"
    assert manifest["candidate_lineage"] == {
        "candidate_id": candidate["candidate_id"],
        "revision_number": 1,
        "candidate_sha256": candidate["candidate_sha256"],
    }
    assert [item["case_id"] for item in manifest["articles"]] == [
        "LK-0001"
    ]


def test_changed_publication_metadata_is_rejected(
    tmp_path,
    monkeypatch,
):
    stored_candidate(tmp_path)
    changed = {
        **ARTICLE,
        "content_sha256": "c" * 64,
    }

    with pytest.raises(
        JournalCandidateFinalizationError,
        match="metadata changed",
    ):
        finalize(
            tmp_path,
            monkeypatch,
            discovery(changed),
        )


def test_ineligible_article_is_rejected_at_finalization(
    tmp_path,
    monkeypatch,
):
    stored_candidate(tmp_path)
    report = {
        "schema_version": "1.0",
        "generated_root": "/generated",
        "eligible": [],
        "rejected": [
            {
                "case_id": "LK-0001",
                "eligible": False,
                "reasons": ["QA verdict is not PASS"],
            }
        ],
    }

    with pytest.raises(
        JournalCandidateFinalizationError,
        match="source revalidation failed",
    ):
        finalize(tmp_path, monkeypatch, report)


def test_finalized_candidate_cannot_receive_revision(
    tmp_path,
    monkeypatch,
):
    candidate = stored_candidate(tmp_path)
    finalize(tmp_path, monkeypatch)

    revision = revise_candidate(
        candidate,
        revised_at_utc="2026-08-18T13:20:00Z",
        articles=[ARTICLE],
    )
    with pytest.raises(
        JournalCandidateStoreError,
        match="finalized and cannot be revised",
    ):
        store_candidate_revision(tmp_path, revision)


def test_duplicate_finalization_is_rejected(
    tmp_path,
    monkeypatch,
):
    stored_candidate(tmp_path)
    finalize(tmp_path, monkeypatch)

    with pytest.raises(
        JournalCandidateFinalizationError,
        match="already finalized",
    ):
        finalize(tmp_path, monkeypatch)


def test_tampered_finalization_manifest_is_rejected(
    tmp_path,
    monkeypatch,
):
    candidate = stored_candidate(tmp_path)
    result = finalize(tmp_path, monkeypatch)
    manifest_path = tmp_path / result["manifest_file"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["title"] = "Tampered"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        JournalCandidateStoreError,
        match="finalization manifest is invalid",
    ):
        load_candidate_finalization(
            tmp_path,
            candidate["candidate_id"],
        )
