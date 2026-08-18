from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from journal.assembly import (
    JournalAssemblyError,
    assemble_journal,
    compute_assembly_sha256,
    validate_assembly,
)
from journal.manifest import finalize_manifest


CONTENT = "<h2>Case Snapshot</h2><p>Certified English article.</p>"


def write_payload(root: Path, content: str = CONTENT) -> str:
    path = (
        root
        / "generated"
        / "LK-0001"
        / "output"
        / "11-publication"
        / "wordpress-final-draft-payload.json"
    )
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "title": "End-Use Over Label: Hostels Are Homes",
                "slug": "end-use-over-label-hostels-are-homes",
                "excerpt": "A certified legal explainer.",
                "content": content,
                "status": "draft",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path.relative_to(root).as_posix()


def build_manifest(root: Path, content: str = CONTENT):
    source_payload = write_payload(root, content)

    return finalize_manifest(
        journal_id="LK-JOURNAL-2026-W34",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal",
        selected_by="Founder",
        finalized_at_utc="2026-08-18T03:45:00Z",
        articles=[
            {
                "case_id": "LK-0001",
                "title": "End-Use Over Label: Hostels Are Homes",
                "slug": "end-use-over-label-hostels-are-homes",
                "source_payload": source_payload,
                "content_sha256": hashlib.sha256(
                    content.encode("utf-8")
                ).hexdigest(),
            }
        ],
    )


def test_assembly_is_deterministic(tmp_path):
    manifest = build_manifest(tmp_path)

    first = assemble_journal(manifest, project_root=tmp_path)
    second = assemble_journal(manifest, project_root=tmp_path)

    assert first == second
    assert first["assembly_sha256"] == compute_assembly_sha256(first)
    validate_assembly(first)


def test_corrected_rendering_scope_is_locked(tmp_path):
    assembly = assemble_journal(
        build_manifest(tmp_path),
        project_root=tmp_path,
    )

    assert assembly["language"] == "en"
    assert assembly["rendering_policy"] == {
        "body_language": "en",
        "tamil_rendering": False,
        "thirukkural_algorithm_usage": "TITLE_ONLY",
        "website_dressing": "DEFERRED_TO_FINAL_SPRINT",
    }


def test_assembly_preserves_selected_order(tmp_path):
    manifest = build_manifest(tmp_path)
    assembly = assemble_journal(manifest, project_root=tmp_path)

    assert [item["position"] for item in assembly["articles"]] == [1]
    assert assembly["articles"][0]["case_id"] == "LK-0001"


def test_content_hash_mismatch_is_rejected(tmp_path):
    manifest = build_manifest(tmp_path)
    payload_path = tmp_path / manifest["articles"][0]["source_payload"]
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["content"] = "<p>Tampered content.</p>"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        JournalAssemblyError,
        match="content hash mismatch",
    ):
        assemble_journal(manifest, project_root=tmp_path)


def test_source_path_escape_is_rejected(tmp_path):
    outside = tmp_path.parent / "outside-journal-payload.json"
    outside.write_text("{}", encoding="utf-8")

    manifest = build_manifest(tmp_path)
    manifest["articles"][0]["source_payload"] = "../outside-journal-payload.json"
    manifest["manifest_sha256"] = hashlib.sha256(b"invalid").hexdigest()

    # Rebuild a valid manifest carrying the unsafe path.
    manifest = finalize_manifest(
        journal_id="LK-JOURNAL-2026-W34",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal",
        selected_by="Founder",
        finalized_at_utc="2026-08-18T03:45:00Z",
        articles=[
            {
                "case_id": "LK-0001",
                "title": "End-Use Over Label: Hostels Are Homes",
                "slug": "end-use-over-label-hostels-are-homes",
                "source_payload": "../outside-journal-payload.json",
                "content_sha256": "a" * 64,
            }
        ],
    )

    with pytest.raises(
        JournalAssemblyError,
        match="escapes the project root",
    ):
        assemble_journal(manifest, project_root=tmp_path)


def test_tampered_assembly_is_rejected(tmp_path):
    assembly = assemble_journal(
        build_manifest(tmp_path),
        project_root=tmp_path,
    )
    tampered = deepcopy(assembly)
    tampered["title"] = "Tampered journal"

    with pytest.raises(
        JournalAssemblyError,
        match="assembly_sha256 does not match",
    ):
        validate_assembly(tampered)
