from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import FormatChecker, validate

from journal.candidate import (
    JournalCandidateError,
    compute_candidate_sha256,
    create_candidate_revision,
    revise_candidate,
    validate_candidate_revision,
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


def test_candidate_creation_is_deterministic():
    assert build_candidate() == build_candidate()


def test_first_revision_contract():
    candidate = build_candidate()
    assert candidate["revision_number"] == 1
    assert candidate["previous_revision_sha256"] is None
    assert candidate["status"] == "CANDIDATE"
    assert candidate["articles"][0]["position"] == 1
    validate_candidate_revision(candidate)


def test_revision_hash_chain_is_append_only():
    first = build_candidate()
    second_article = {
        **ARTICLE,
        "case_id": "LK-0002",
        "slug": "second-certified-article",
        "content_sha256": "c" * 64,
        "publication_evidence_sha256": "d" * 64,
    }
    second = revise_candidate(
        first,
        revised_at_utc="2026-08-18T13:05:00Z",
        articles=[second_article, ARTICLE],
    )
    assert second["revision_number"] == 2
    assert second["previous_revision_sha256"] == first[
        "candidate_sha256"
    ]
    assert [item["case_id"] for item in second["articles"]] == [
        "LK-0002",
        "LK-0001",
    ]


def test_tampered_candidate_is_rejected():
    candidate = build_candidate()
    candidate["title"] = "Tampered"
    with pytest.raises(
        JournalCandidateError,
        match="candidate_sha256 does not match",
    ):
        validate_candidate_revision(candidate)


def test_duplicate_case_selection_is_rejected():
    with pytest.raises(
        JournalCandidateError,
        match="duplicate selected case_id",
    ):
        create_candidate_revision(
            candidate_id="LK-CANDIDATE-2026-W34",
            journal_id="LK-JOURNAL-2026-W34",
            edition_date="2026-08-23",
            title="LegalKural Weekly Journal",
            editor="Founder",
            revised_at_utc="2026-08-18T13:00:00Z",
            articles=[ARTICLE, ARTICLE],
        )


def test_revision_timestamp_must_advance():
    with pytest.raises(
        JournalCandidateError,
        match="timestamp must be later",
    ):
        revise_candidate(
            build_candidate(),
            revised_at_utc="2026-08-18T13:00:00Z",
            articles=[ARTICLE],
        )


def test_invalid_previous_hash_is_rejected():
    candidate = build_candidate()
    candidate["revision_number"] = 2
    candidate["previous_revision_sha256"] = "invalid"
    candidate["candidate_sha256"] = compute_candidate_sha256(candidate)
    with pytest.raises(
        JournalCandidateError,
        match="previous_revision_sha256",
    ):
        validate_candidate_revision(candidate)


def test_candidate_matches_json_schema():
    schema_path = (
        Path(__file__).parents[1]
        / "schemas"
        / "weekly_journal_candidate.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(
        instance=build_candidate(),
        schema=schema,
        format_checker=FormatChecker(),
    )


def test_invalid_article_slug_is_rejected():
    article = {**ARTICLE, "slug": "Invalid Slug"}
    with pytest.raises(
        JournalCandidateError,
        match="lowercase hyphenated slug",
    ):
        create_candidate_revision(
            candidate_id="LK-CANDIDATE-2026-W34",
            journal_id="LK-JOURNAL-2026-W34",
            edition_date="2026-08-23",
            title="LegalKural Weekly Journal",
            editor="Founder",
            revised_at_utc="2026-08-18T13:00:00Z",
            articles=[article],
        )


def test_unexpected_candidate_field_is_rejected():
    candidate = build_candidate()
    candidate["unexpected"] = True
    candidate["candidate_sha256"] = compute_candidate_sha256(candidate)
    with pytest.raises(
        JournalCandidateError,
        match="fields do not match",
    ):
        validate_candidate_revision(candidate)
