import hashlib
import json
from pathlib import Path

import pytest

from journal.discovery import (
    JournalDiscoveryError,
    discover_articles,
    select_articles,
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )


def create_case(
    generated_root: Path,
    case_id: str,
    *,
    title: str = "End-Use Over Label: Hostels Are Homes",
    slug: str = "end-use-over-label-hostels-are-homes",
    content: str = "<p>Certified LegalKural article.</p>",
) -> Path:
    case_root = generated_root / case_id
    publication_root = case_root / "output" / "11-publication"
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    write_json(
        case_root / "evidence" / "validation-report.json",
        {
            "schema_version": "1.0",
            "case_id": case_id,
            "status": "COMPLETE",
            "verdict": "PASS",
            "publication_ready": True,
        },
    )
    write_json(
        publication_root / "wordpress-final-draft-payload.json",
        {
            "title": title,
            "slug": slug,
            "content": content,
            "excerpt": "Certified article.",
            "status": "draft",
        "author": 101,
        "categories": [201],
        "tags": [303, 302, 301],
        },
    )
    write_json(
        publication_root / "wordpress-publication-evidence.json",
        {
            "schema_version": "1.0",
            "case_id": case_id,
            "post_id": 10,
            "status": "publish",
            "slug": slug,
            "link": f"https://example.test/{slug}/",
            "content_hash": content_hash,
            "publication_performed": True,
            "published_at": "2026-08-17T14:51:33",
        "author": 101,
        "categories": [201],
        "tags": [301, 302, 303],
        },
    )
    return case_root


def test_discovers_certified_published_article(tmp_path):
    generated = tmp_path / "generated"
    create_case(generated, "LK-0001")

    report = discover_articles(generated)

    assert [item["case_id"] for item in report["eligible"]] == ["LK-0001"]
    assert report["rejected"] == []
    assert report["eligible"][0]["post_id"] == 10


def test_discovery_order_is_stable(tmp_path):
    generated = tmp_path / "generated"
    create_case(generated, "LK-0002", slug="second")
    create_case(generated, "LK-0001", slug="first")

    report = discover_articles(generated)

    assert [item["case_id"] for item in report["eligible"]] == [
        "LK-0001",
        "LK-0002",
    ]


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (
            lambda root: write_json(
                root / "evidence" / "validation-report.json",
                {
                    "verdict": "REVIEW_REQUIRED",
                    "publication_ready": False,
                },
            ),
            "QA verdict is not PASS",
        ),
        (
            lambda root: (
                root
                / "output"
                / "11-publication"
                / "wordpress-publication-evidence.json"
            ).unlink(),
            "missing required artifact: publication_evidence",
        ),
    ],
)
def test_rejects_ineligible_case(tmp_path, change, reason):
    generated = tmp_path / "generated"
    case_root = create_case(generated, "LK-0001")
    change(case_root)

    report = discover_articles(generated)

    assert report["eligible"] == []
    assert reason in report["rejected"][0]["reasons"]


def test_rejects_content_hash_mismatch(tmp_path):
    generated = tmp_path / "generated"
    case_root = create_case(generated, "LK-0001")
    payload_path = (
        case_root
        / "output"
        / "11-publication"
        / "wordpress-final-draft-payload.json"
    )
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["content"] = "<p>Tampered after publication.</p>"
    write_json(payload_path, payload)

    report = discover_articles(generated)

    assert report["eligible"] == []
    assert (
        "published content hash differs from final payload"
        in report["rejected"][0]["reasons"]
    )


def test_editor_selection_is_explicit_and_ordered(tmp_path):
    generated = tmp_path / "generated"
    create_case(generated, "LK-0001", slug="first")
    create_case(generated, "LK-0002", slug="second")
    report = discover_articles(generated)

    selected = select_articles(report, ["LK-0002", "LK-0001"])

    assert [item["case_id"] for item in selected] == [
        "LK-0002",
        "LK-0001",
    ]
    assert [item["slug"] for item in selected] == ["second", "first"]


def test_selection_rejects_duplicate_case_ids(tmp_path):
    generated = tmp_path / "generated"
    create_case(generated, "LK-0001")
    report = discover_articles(generated)

    with pytest.raises(
        JournalDiscoveryError,
        match="duplicate case_ids",
    ):
        select_articles(report, ["LK-0001", "LK-0001"])


def test_selection_rejects_ineligible_case(tmp_path):
    generated = tmp_path / "generated"
    create_case(generated, "LK-0001")
    report = discover_articles(generated)

    with pytest.raises(
        JournalDiscoveryError,
        match="not eligible",
    ):
        select_articles(report, ["LK-NOT-ELIGIBLE"])


def test_non_case_generated_directories_are_ignored(tmp_path):
    generated = tmp_path / "generated"
    create_case(generated, "LK-0001")
    (generated / "wordpress").mkdir(parents=True)

    report = discover_articles(generated)

    assert [item["case_id"] for item in report["eligible"]] == ["LK-0001"]
    assert report["rejected"] == []


def test_discovery_preserves_normalized_publication_metadata(tmp_path):
    generated = tmp_path / "generated"
    create_case(generated, "LK-0001")
    article = discover_articles(generated)["eligible"][0]

    assert article["published_url"] == (
        "https://example.test/"
        "end-use-over-label-hostels-are-homes/"
    )
    assert article["published_at"] == "2026-08-17T14:51:33"
    assert article["author"] == 101
    assert article["categories"] == [201]
    assert article["tags"] == [301, 302, 303]
    assert article["publication_evidence_sha256"]


def test_rejects_publication_taxonomy_mismatch(tmp_path):
    generated = tmp_path / "generated"
    case_root = create_case(generated, "LK-0001")
    payload_path = (
        case_root
        / "output"
        / "11-publication"
        / "wordpress-final-draft-payload.json"
    )
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["tags"] = [999]
    write_json(payload_path, payload)

    report = discover_articles(generated)

    assert report["eligible"] == []
    assert (
        "payload and publication tags differ"
        in report["rejected"][0]["reasons"]
    )


def test_editor_selection_preserves_publication_lineage(tmp_path):
    generated = tmp_path / "generated"
    create_case(generated, "LK-0001")
    report = discover_articles(generated)
    selected = select_articles(report, ["LK-0001"])
    article = selected[0]

    assert article["author"] == 101
    assert article["categories"] == [201]
    assert article["tags"] == [301, 302, 303]
    assert article["published_at"] == "2026-08-17T14:51:33"
    assert article["published_url"].startswith("https://")
    assert article["publication_evidence"]
    assert article["publication_evidence_sha256"]
