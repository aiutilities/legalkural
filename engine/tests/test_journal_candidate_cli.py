import json

import pytest

import journal.cli as cli
from journal.discovery import JournalDiscoveryError


ARTICLE_ONE = {
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

ARTICLE_TWO = {
    "eligible": True,
    "case_id": "LK-0002",
    "title": "Second Certified Article",
    "slug": "second-certified-article",
    "source_payload": "generated/LK-0002/payload.json",
    "content_sha256": "c" * 64,
    "publication_evidence": "generated/LK-0002/evidence.json",
    "publication_evidence_sha256": "d" * 64,
    "post_id": 102,
    "published_url": "https://example.test/second/",
    "published_at": "2026-08-18T10:00:00",
    "author": 201,
    "categories": [301],
    "tags": [401, 403],
}


def discovery():
    return {
        "schema_version": "1.0",
        "generated_root": "/generated",
        "eligible": [ARTICLE_ONE, ARTICLE_TWO],
        "rejected": [],
    }


def create_arguments(storage_root):
    return [
        "candidate-create",
        "--storage-root",
        str(storage_root),
        "--generated-root",
        "unused",
        "--candidate-id",
        "LK-CANDIDATE-2026-W34",
        "--journal-id",
        "LK-JOURNAL-2026-W34",
        "--edition-date",
        "2026-08-23",
        "--title",
        "LegalKural Weekly Journal",
        "--editor",
        "Founder",
        "--revised-at-utc",
        "2026-08-18T13:00:00Z",
        "--case-id",
        "LK-0001",
    ]


def run_json(arguments, capsys):
    assert cli.main(arguments) == 0
    return json.loads(capsys.readouterr().out)


@pytest.mark.parametrize(
    "command",
    (
        "candidate-create",
        "candidate-inspect",
        "candidate-list",
        "candidate-revise",
    ),
)
def test_parser_exposes_candidate_editorial_commands(command, capsys):
    parser = cli.build_parser()
    with pytest.raises(SystemExit) as exit_info:
        parser.parse_args([command, "--help"])

    assert exit_info.value.code == 0
    assert f"legalkural-journal {command}" in capsys.readouterr().out


def test_candidate_create_stores_explicit_selection(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(cli, "discover_articles", lambda unused: discovery())

    result = run_json(create_arguments(tmp_path), capsys)

    assert result["status"] == "STORED"
    assert result["revision_number"] == 1
    assert result["selected_case_ids"] == ["LK-0001"]


def test_candidate_inspect_reads_stored_revision(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(cli, "discover_articles", lambda unused: discovery())
    run_json(create_arguments(tmp_path), capsys)

    result = run_json(
        [
            "candidate-inspect",
            "--storage-root",
            str(tmp_path),
            "--candidate-id",
            "LK-CANDIDATE-2026-W34",
            "--revision",
            "1",
        ],
        capsys,
    )

    assert result["revision_number"] == 1
    assert result["articles"][0]["case_id"] == "LK-0001"


def test_candidate_list_returns_revision_summaries(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(cli, "discover_articles", lambda unused: discovery())
    run_json(create_arguments(tmp_path), capsys)

    result = run_json(
        [
            "candidate-list",
            "--storage-root",
            str(tmp_path),
            "--candidate-id",
            "LK-CANDIDATE-2026-W34",
        ],
        capsys,
    )

    assert result["revision_count"] == 1
    assert result["revisions"][0]["selected_case_ids"] == ["LK-0001"]


def test_candidate_revise_preserves_requested_order(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(cli, "discover_articles", lambda unused: discovery())
    run_json(create_arguments(tmp_path), capsys)

    result = run_json(
        [
            "candidate-revise",
            "--storage-root",
            str(tmp_path),
            "--generated-root",
            "unused",
            "--candidate-id",
            "LK-CANDIDATE-2026-W34",
            "--revised-at-utc",
            "2026-08-18T13:05:00Z",
            "--case-id",
            "LK-0002",
            "--case-id",
            "LK-0001",
        ],
        capsys,
    )

    assert result["revision_number"] == 2
    assert result["selected_case_ids"] == ["LK-0002", "LK-0001"]


def test_candidate_revise_can_remove_an_article(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(cli, "discover_articles", lambda unused: discovery())
    create = create_arguments(tmp_path)
    create.extend(["--case-id", "LK-0002"])
    run_json(create, capsys)

    result = run_json(
        [
            "candidate-revise",
            "--storage-root",
            str(tmp_path),
            "--generated-root",
            "unused",
            "--candidate-id",
            "LK-CANDIDATE-2026-W34",
            "--revised-at-utc",
            "2026-08-18T13:05:00Z",
            "--case-id",
            "LK-0002",
        ],
        capsys,
    )

    assert result["selected_case_ids"] == ["LK-0002"]


def test_ineligible_addition_is_rejected(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(cli, "discover_articles", lambda unused: discovery())

    arguments = create_arguments(tmp_path)
    arguments[-1] = "LK-INELIGIBLE"

    with pytest.raises(
        JournalDiscoveryError,
        match="not eligible",
    ):
        cli.main(arguments)


def test_duplicate_selection_is_rejected(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(cli, "discover_articles", lambda unused: discovery())

    arguments = create_arguments(tmp_path)
    arguments.extend(["--case-id", "LK-0001"])

    with pytest.raises(
        JournalDiscoveryError,
        match="duplicate",
    ):
        cli.main(arguments)
