from copy import deepcopy
import json

import pytest

from journal.candidate import (
    compute_candidate_sha256,
    create_candidate_revision,
    revise_candidate,
)
from journal.candidate_store import (
    JournalCandidateStoreError,
    list_candidate_revisions,
    load_candidate_revision,
    store_candidate_revision,
)


ARTICLE = {
    "case_id": "LK-0001",
    "title": "First Certified Article",
    "slug": "first-certified-article",
    "source_payload": "generated/LK-0001/payload.json",
    "content_sha256": "a" * 64,
    "publication_evidence": "generated/LK-0001/evidence.json",
    "publication_evidence_sha256": "b" * 64,
    "published_url": "https://example.test/first/",
    "published_at": "2026-08-17T10:00:00",
    "author": 101,
    "categories": [201],
    "tags": [301, 302],
}


def build_candidate():
    return create_candidate_revision(
        candidate_id="LK-CANDIDATE-2026-W34",
        journal_id="LK-JOURNAL-2026-W34",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal",
        editor="Founder",
        revised_at_utc="2026-08-18T13:00:00Z",
        articles=[ARTICLE],
    )


def test_first_revision_is_stored_and_loaded(tmp_path):
    candidate = build_candidate()
    result = store_candidate_revision(tmp_path, candidate)

    assert result["status"] == "STORED"
    assert result["revision_number"] == 1
    assert result["revision_file"].endswith(
        "revisions/000001/candidate.json"
    )
    assert load_candidate_revision(
        tmp_path,
        candidate["candidate_id"],
    ) == candidate


def test_revision_history_is_appended_in_order(tmp_path):
    first = build_candidate()
    store_candidate_revision(tmp_path, first)

    second = revise_candidate(
        first,
        revised_at_utc="2026-08-18T13:05:00Z",
        articles=[ARTICLE],
    )
    store_candidate_revision(tmp_path, second)

    revisions = list_candidate_revisions(
        tmp_path,
        first["candidate_id"],
    )
    assert [item["revision_number"] for item in revisions] == [1, 2]
    assert revisions[1]["previous_revision_sha256"] == (
        revisions[0]["candidate_sha256"]
    )


def test_existing_revision_cannot_be_overwritten(tmp_path):
    candidate = build_candidate()
    store_candidate_revision(tmp_path, candidate)

    with pytest.raises(
        JournalCandidateStoreError,
        match="next revision must be 2",
    ):
        store_candidate_revision(tmp_path, candidate)


def test_revision_gap_is_rejected(tmp_path):
    candidate = build_candidate()
    candidate["revision_number"] = 2
    candidate["previous_revision_sha256"] = "c" * 64
    candidate["candidate_sha256"] = compute_candidate_sha256(candidate)

    with pytest.raises(
        JournalCandidateStoreError,
        match="next revision must be 1",
    ):
        store_candidate_revision(tmp_path, candidate)


def test_broken_hash_chain_is_rejected(tmp_path):
    first = build_candidate()
    store_candidate_revision(tmp_path, first)

    second = revise_candidate(
        first,
        revised_at_utc="2026-08-18T13:05:00Z",
        articles=[ARTICLE],
    )
    second["previous_revision_sha256"] = "c" * 64
    second["candidate_sha256"] = compute_candidate_sha256(second)

    with pytest.raises(
        JournalCandidateStoreError,
        match="does not extend",
    ):
        store_candidate_revision(tmp_path, second)


def test_tampered_stored_revision_is_rejected(tmp_path):
    candidate = build_candidate()
    result = store_candidate_revision(tmp_path, candidate)
    stored_path = tmp_path / result["revision_file"]

    value = json.loads(stored_path.read_text(encoding="utf-8"))
    value["title"] = "Tampered"
    stored_path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(
        JournalCandidateStoreError,
        match="stored candidate revision is invalid",
    ):
        load_candidate_revision(
            tmp_path,
            candidate["candidate_id"],
        )


def test_candidate_directory_symlink_is_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    candidate = build_candidate()
    candidate_link = tmp_path / candidate["candidate_id"]
    candidate_link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(
        JournalCandidateStoreError,
        match="cannot be a symlink",
    ):
        store_candidate_revision(tmp_path, candidate)


def test_unexpected_storage_entry_is_rejected(tmp_path):
    candidate = build_candidate()
    store_candidate_revision(tmp_path, candidate)

    revisions = (
        tmp_path
        / candidate["candidate_id"]
        / "revisions"
    )
    (revisions / "unexpected").mkdir()

    with pytest.raises(
        JournalCandidateStoreError,
        match="unexpected candidate storage entry",
    ):
        list_candidate_revisions(
            tmp_path,
            candidate["candidate_id"],
        )
