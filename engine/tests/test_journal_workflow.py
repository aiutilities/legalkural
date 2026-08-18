from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from pypdf import PdfReader

from journal.workflow import (
    JournalWorkflowError,
    build_weekly_journal,
    compute_evidence_sha256,
    validate_build_evidence,
    verify_journal_edition,
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def create_eligible_case(
    project_root: Path,
    case_id: str,
    slug: str,
) -> None:
    generated = project_root / "generated"
    case_root = generated / case_id
    publication = case_root / "output" / "11-publication"
    content = (
        f"<h2>Case Snapshot</h2>"
        f"<p>Certified English content for {case_id}.</p>"
    )
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    write_json(
        case_root / "evidence" / "validation-report.json",
        {
            "verdict": "PASS",
            "publication_ready": True,
        },
    )
    write_json(
        publication / "wordpress-final-draft-payload.json",
        {
            "title": f"Article {case_id}",
            "slug": slug,
            "excerpt": "Certified article.",
            "content": content,
            "status": "draft",
        "author": 101,
        "categories": [201],
        "tags": [303, 302, 301],
        },
    )
    write_json(
        publication / "wordpress-publication-evidence.json",
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


def build(root: Path, case_ids=None):
    return build_weekly_journal(
        project_root=root,
        generated_root=root / "generated",
        output_root=root / "journals",
        journal_id="LK-JOURNAL-2026-W34",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal",
        selected_by="Founder",
        finalized_at_utc="2026-08-18T05:15:00Z",
        case_ids=case_ids or ["LK-0001"],
    )


def test_atomic_workflow_writes_complete_edition(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    result = build(tmp_path)
    output = Path(result["output_directory"])

    assert sorted(path.name for path in output.iterdir()) == [
        "assembly.json",
        "build-evidence.json",
        "journal.pdf",
        "manifest.json",
    ]
    assert result["status"] == "COMPLETE"
    assert result["provider_requests"] == 0
    assert result["wordpress_requests"] == 0
    assert len(PdfReader(str(output / "journal.pdf")).pages) >= 2


def test_duplicate_journal_id_is_rejected(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    build(tmp_path)

    with pytest.raises(
        JournalWorkflowError,
        match="already exists",
    ):
        build(tmp_path)


def test_editor_order_flows_into_manifest(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    create_eligible_case(tmp_path, "LK-0002", "second")

    result = build(tmp_path, ["LK-0002", "LK-0001"])
    output = Path(result["output_directory"])
    manifest = json.loads(
        (output / "manifest.json").read_text(encoding="utf-8")
    )

    assert [
        article["case_id"]
        for article in manifest["articles"]
    ] == ["LK-0002", "LK-0001"]


def test_tampered_evidence_is_rejected(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    result = build(tmp_path)
    evidence = deepcopy(result)
    evidence.pop("output_directory")
    evidence["article_count"] = 99

    with pytest.raises(
        JournalWorkflowError,
        match="evidence_sha256 does not match",
    ):
        validate_build_evidence(evidence)


def test_evidence_digest_is_self_excluding(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    result = build(tmp_path)
    result.pop("output_directory")

    assert result["evidence_sha256"] == compute_evidence_sha256(result)


def test_complete_multi_article_edition_is_verified(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    create_eligible_case(tmp_path, "LK-0002", "second")
    result = build(tmp_path, ["LK-0002", "LK-0001"])

    verified = verify_journal_edition(
        Path(result["output_directory"])
    )

    assert verified["verification_status"] == "VERIFIED"
    assert verified["article_count"] == 2
    assert verified["selected_case_ids"] == ["LK-0002", "LK-0001"]
    assert verified["provider_requests"] == 0
    assert verified["wordpress_requests"] == 0
    assert verified["language"] == "en"
    assert verified["tamil_rendered"] is False
    assert verified["thirukkural_algorithm_usage"] == "TITLE_ONLY"


def test_modified_pdf_is_rejected_by_edition_verifier(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    result = build(tmp_path)
    pdf_path = Path(result["output_directory"]) / "journal.pdf"
    pdf_path.write_bytes(pdf_path.read_bytes() + b"TAMPERED")

    with pytest.raises(
        JournalWorkflowError,
        match="PDF SHA-256 mismatch",
    ):
        verify_journal_edition(Path(result["output_directory"]))


def test_modified_manifest_is_rejected_by_edition_verifier(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    result = build(tmp_path)
    output = Path(result["output_directory"])
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["title"] = "Tampered title"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        JournalWorkflowError,
        match="artifact validation failed",
    ):
        verify_journal_edition(output)


def test_unexpected_edition_file_is_rejected(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    result = build(tmp_path)
    output = Path(result["output_directory"])
    (output / "unexpected.txt").write_text("not approved", encoding="utf-8")

    with pytest.raises(
        JournalWorkflowError,
        match="exactly four approved artifacts",
    ):
        verify_journal_edition(output)


def test_build_evidence_schema_matches_runtime_contract():
    schema_path = (
        Path(__file__).parents[1]
        / "schemas"
        / "weekly_journal_build_evidence.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "schema_version",
        "journal_id",
        "edition_date",
        "status",
        "selected_by",
        "finalized_at_utc",
        "selected_case_ids",
        "article_count",
        "manifest_sha256",
        "assembly_sha256",
        "pdf_sha256",
        "pdf_page_count",
        "pdf_byte_count",
        "renderer_version",
        "language",
        "tamil_rendered",
        "thirukkural_algorithm_usage",
        "provider_requests",
        "wordpress_requests",
        "files",
        "evidence_sha256",
    }
    assert schema["properties"]["language"]["const"] == "en"
    assert schema["properties"]["tamil_rendered"]["const"] is False
    assert (
        schema["properties"]["thirukkural_algorithm_usage"]["const"]
        == "TITLE_ONLY"
    )
    assert schema["properties"]["provider_requests"]["const"] == 0
    assert schema["properties"]["wordpress_requests"]["const"] == 0


def test_build_evidence_records_renderer_version(tmp_path):
    create_eligible_case(tmp_path, "LK-0001", "first")
    result = build(tmp_path)
    output = Path(result["output_directory"])
    evidence = json.loads(
        (output / "build-evidence.json").read_text(encoding="utf-8")
    )

    assert evidence["renderer_version"] == "1.0.0"
    assert verify_journal_edition(output)["renderer_version"] == "1.0.0"
