from copy import deepcopy

import pytest

from journal.manifest import (
    JournalManifestError,
    canonical_json_bytes,
    compute_manifest_sha256,
    finalize_manifest,
    validate_finalized_manifest,
)


ARTICLE = {
    "case_id": "LK-OPENAI-PILOT-0001",
    "title": "End-Use Over Label: Hostels Are Homes",
    "slug": "end-use-over-label-hostels-are-homes",
    "source_payload": (
        "generated/LK-OPENAI-PILOT-0001/"
        "wordpress-final-draft-payload.json"
    ),
    "content_sha256": "a" * 64,
    "publication_evidence": (
        "generated/LK-OPENAI-PILOT-0001/"
        "wordpress-publication-evidence.json"
    ),
    "publication_evidence_sha256": "c" * 64,
    "published_url": "https://example.test/hostels-are-homes/",
    "published_at": "2026-08-17T14:51:33",
    "author": 101,
    "categories": [201],
    "tags": [301, 302, 303],
}


def build_manifest():
    return finalize_manifest(
        journal_id="LK-JOURNAL-2026-W34",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal",
        selected_by="Founder",
        finalized_at_utc="2026-08-17T15:30:00Z",
        articles=[ARTICLE],
    )


def test_finalization_is_deterministic():
    first = build_manifest()
    second = build_manifest()

    assert first == second
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert first["manifest_sha256"] == compute_manifest_sha256(first)


def test_manifest_is_explicitly_english_only():
    manifest = build_manifest()

    assert manifest["language"] == "en"


def test_article_positions_are_assigned_deterministically():
    second_article = {
        **ARTICLE,
        "case_id": "LK-SYNTHETIC-0002",
        "slug": "synthetic-second-article",
        "content_sha256": "b" * 64,
    }

    manifest = finalize_manifest(
        journal_id="LK-JOURNAL-2026-W34",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal",
        selected_by="Founder",
        finalized_at_utc="2026-08-17T15:30:00Z",
        articles=[ARTICLE, second_article],
    )

    assert [item["position"] for item in manifest["articles"]] == [1, 2]


def test_duplicate_case_id_is_rejected():
    duplicate = {
        **ARTICLE,
        "slug": "duplicate-article",
        "content_sha256": "b" * 64,
    }

    with pytest.raises(JournalManifestError, match="duplicate case_id"):
        finalize_manifest(
            journal_id="LK-JOURNAL-2026-W34",
            edition_date="2026-08-23",
            title="LegalKural Weekly Journal",
            selected_by="Founder",
            finalized_at_utc="2026-08-17T15:30:00Z",
            articles=[ARTICLE, duplicate],
        )


def test_duplicate_content_is_rejected():
    duplicate = {
        **ARTICLE,
        "case_id": "LK-SYNTHETIC-0002",
        "slug": "duplicate-content",
    }

    with pytest.raises(
        JournalManifestError,
        match="duplicate article content",
    ):
        finalize_manifest(
            journal_id="LK-JOURNAL-2026-W34",
            edition_date="2026-08-23",
            title="LegalKural Weekly Journal",
            selected_by="Founder",
            finalized_at_utc="2026-08-17T15:30:00Z",
            articles=[ARTICLE, duplicate],
        )


def test_empty_selection_is_rejected():
    with pytest.raises(
        JournalManifestError,
        match="at least one article",
    ):
        finalize_manifest(
            journal_id="LK-JOURNAL-2026-W34",
            edition_date="2026-08-23",
            title="LegalKural Weekly Journal",
            selected_by="Founder",
            finalized_at_utc="2026-08-17T15:30:00Z",
            articles=[],
        )


def test_tampered_manifest_is_rejected():
    manifest = build_manifest()
    tampered = deepcopy(manifest)
    tampered["title"] = "Tampered title"

    with pytest.raises(
        JournalManifestError,
        match="manifest_sha256 does not match",
    ):
        validate_finalized_manifest(tampered)


def test_tamil_journal_language_is_out_of_scope():
    manifest = build_manifest()
    manifest["language"] = "ta"
    manifest["manifest_sha256"] = compute_manifest_sha256(manifest)

    with pytest.raises(
        JournalManifestError,
        match="must be English",
    ):
        validate_finalized_manifest(manifest)


def test_finalized_manifest_matches_json_schema():
    import json
    from pathlib import Path

    from jsonschema import FormatChecker, validate

    schema_path = (
        Path(__file__).parents[1]
        / "schemas"
        / "weekly_journal_manifest.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    validate(
        instance=build_manifest(),
        schema=schema,
        format_checker=FormatChecker(),
    )


def test_manifest_preserves_publication_lineage():
    manifest = build_manifest()
    article = manifest["articles"][0]

    assert manifest["article_count"] == 1
    assert manifest["covered_date_range"] == {
        "start": "2026-08-17",
        "end": "2026-08-17",
    }
    assert article["author"] == 101
    assert article["categories"] == [201]
    assert article["tags"] == [301, 302, 303]
    assert article["published_url"].startswith("https://")
    assert article["publication_evidence_sha256"] == "c" * 64


def test_manifest_covered_range_uses_publication_dates():
    second_article = {
        **ARTICLE,
        "case_id": "LK-SYNTHETIC-0002",
        "slug": "synthetic-second",
        "content_sha256": "b" * 64,
        "publication_evidence_sha256": "d" * 64,
        "published_at": "2026-08-15T09:00:00",
    }
    manifest = finalize_manifest(
        journal_id="LK-JOURNAL-2026-W34",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal",
        selected_by="Founder",
        finalized_at_utc="2026-08-17T15:30:00Z",
        articles=[ARTICLE, second_article],
    )

    assert manifest["article_count"] == 2
    assert manifest["covered_date_range"] == {
        "start": "2026-08-15",
        "end": "2026-08-17",
    }


def test_invalid_covered_date_range_is_rejected():
    manifest = build_manifest()
    manifest["covered_date_range"]["start"] = "2026-08-01"
    manifest["manifest_sha256"] = compute_manifest_sha256(manifest)

    with pytest.raises(
        JournalManifestError,
        match="covered_date_range",
    ):
        validate_finalized_manifest(manifest)


CANDIDATE_LINEAGE = {
    "candidate_id": "LK-CANDIDATE-2026-W34",
    "revision_number": 2,
    "candidate_sha256": "e" * 64,
}


def build_candidate_manifest():
    return finalize_manifest(
        journal_id="LK-JOURNAL-2026-W34",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal",
        selected_by="Founder",
        finalized_at_utc="2026-08-17T15:30:00Z",
        articles=[ARTICLE],
        candidate_lineage=CANDIDATE_LINEAGE,
    )


def test_candidate_lineage_is_preserved_and_hash_protected():
    manifest = build_candidate_manifest()

    assert manifest["candidate_lineage"] == CANDIDATE_LINEAGE
    assert manifest["manifest_sha256"] == compute_manifest_sha256(
        manifest
    )
    validate_finalized_manifest(manifest)


def test_legacy_manifest_remains_without_candidate_lineage():
    manifest = build_manifest()

    assert "candidate_lineage" not in manifest
    validate_finalized_manifest(manifest)


def test_invalid_candidate_lineage_is_rejected():
    invalid = {
        **CANDIDATE_LINEAGE,
        "candidate_sha256": "invalid",
    }

    with pytest.raises(
        JournalManifestError,
        match="candidate_lineage.candidate_sha256",
    ):
        finalize_manifest(
            journal_id="LK-JOURNAL-2026-W34",
            edition_date="2026-08-23",
            title="LegalKural Weekly Journal",
            selected_by="Founder",
            finalized_at_utc="2026-08-17T15:30:00Z",
            articles=[ARTICLE],
            candidate_lineage=invalid,
        )


def test_candidate_manifest_matches_json_schema():
    import json
    from pathlib import Path

    from jsonschema import FormatChecker, validate

    schema_path = (
        Path(__file__).parents[1]
        / "schemas"
        / "weekly_journal_manifest.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(
        instance=build_candidate_manifest(),
        schema=schema,
        format_checker=FormatChecker(),
    )
