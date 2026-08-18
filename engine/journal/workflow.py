"""Atomic offline weekly-journal build workflow."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

from .assembly import assemble_journal, validate_assembly
from .candidate_store import (
    JournalCandidateStoreError,
    load_candidate_finalization,
)
from .discovery import discover_articles, select_articles
from .manifest import (
    canonical_json_bytes,
    finalize_manifest,
    validate_finalized_manifest,
)
from .renderer import render_journal_pdf


JOURNAL_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]+$")


class JournalWorkflowError(RuntimeError):
    """Raised when an offline journal build cannot complete safely."""


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value) + b"\n")


def compute_evidence_sha256(evidence: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(evidence))
    payload.pop("evidence_sha256", None)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


EVIDENCE_KEYS = {
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


def validate_build_evidence(evidence: Mapping[str, Any]) -> None:
    if set(evidence) != EVIDENCE_KEYS:
        raise JournalWorkflowError("unexpected build evidence fields")
    if evidence.get("schema_version") != "1.0":
        raise JournalWorkflowError("unsupported evidence schema_version")

    if evidence.get("status") != "COMPLETE":
        raise JournalWorkflowError("journal build evidence is not COMPLETE")

    if evidence.get("provider_requests") != 0:
        raise JournalWorkflowError("provider request count must remain zero")

    if evidence.get("wordpress_requests") != 0:
        raise JournalWorkflowError("WordPress request count must remain zero")

    files = evidence.get("files")
    if not isinstance(files, Mapping):
        raise JournalWorkflowError("evidence file map is missing")

    if set(files) != {
        "manifest",
        "assembly",
        "pdf",
        "evidence",
    }:
        raise JournalWorkflowError("unexpected evidence file map")

    supplied = evidence.get("evidence_sha256")
    if not isinstance(supplied, str):
        raise JournalWorkflowError("evidence_sha256 is missing")

    if supplied != compute_evidence_sha256(evidence):
        raise JournalWorkflowError(
            "evidence_sha256 does not match content"
        )

    hash_pattern = re.compile(r"^[0-9a-f]{64}$")
    for field in (
        "manifest_sha256",
        "assembly_sha256",
        "pdf_sha256",
        "evidence_sha256",
    ):
        value = evidence.get(field)
        if not isinstance(value, str) or not hash_pattern.fullmatch(value):
            raise JournalWorkflowError(f"{field} must be a SHA-256 digest")

    case_ids = evidence.get("selected_case_ids")
    if (
        not isinstance(case_ids, list)
        or not case_ids
        or any(not isinstance(value, str) or not value for value in case_ids)
        or len(case_ids) != len(set(case_ids))
    ):
        raise JournalWorkflowError(
            "selected_case_ids must be a non-empty unique string list"
        )
    if evidence.get("article_count") != len(case_ids):
        raise JournalWorkflowError(
            "article_count does not match selected_case_ids"
        )
    for field in ("pdf_page_count", "pdf_byte_count"):
        value = evidence.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise JournalWorkflowError(f"{field} must be a positive integer")
    if evidence.get("renderer_version") != "1.0.0":
        raise JournalWorkflowError(
            "unsupported journal renderer_version"
        )
    if evidence.get("language") != "en":
        raise JournalWorkflowError("journal language must be en")
    if evidence.get("tamil_rendered") is not False:
        raise JournalWorkflowError("Tamil rendering must remain disabled")
    if evidence.get("thirukkural_algorithm_usage") != "TITLE_ONLY":
        raise JournalWorkflowError(
            "Thirukkural algorithm usage must remain TITLE_ONLY"
        )


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JournalWorkflowError(
            f"cannot read journal JSON artifact: {path.name}"
        ) from exc
    if not isinstance(value, dict):
        raise JournalWorkflowError(
            f"journal JSON artifact must be an object: {path.name}"
        )
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_journal_edition(
    edition_directory: Path,
) -> dict[str, Any]:
    """Revalidate a complete offline journal edition and its evidence."""
    edition = edition_directory.expanduser().resolve()
    if not edition.is_dir():
        raise JournalWorkflowError("journal edition directory is missing")

    expected_names = {
        "manifest.json",
        "assembly.json",
        "journal.pdf",
        "build-evidence.json",
    }
    actual_names = {path.name for path in edition.iterdir()}
    if actual_names != expected_names:
        raise JournalWorkflowError(
            "journal edition must contain exactly four approved artifacts"
        )

    paths = {name: edition / name for name in expected_names}
    if any(path.is_symlink() or not path.is_file() for path in paths.values()):
        raise JournalWorkflowError(
            "journal edition artifacts must be regular files"
        )

    evidence = _read_json_object(paths["build-evidence.json"])
    manifest = _read_json_object(paths["manifest.json"])
    assembly = _read_json_object(paths["assembly.json"])

    validate_build_evidence(evidence)
    try:
        validate_finalized_manifest(manifest)
        validate_assembly(assembly)
    except ValueError as exc:
        raise JournalWorkflowError(
            f"journal artifact validation failed: {exc}"
        ) from exc

    canonical_files = {
        "manifest.json": canonical_json_bytes(manifest) + b"\n",
        "assembly.json": canonical_json_bytes(assembly) + b"\n",
        "build-evidence.json": canonical_json_bytes(evidence) + b"\n",
    }
    for name, expected_bytes in canonical_files.items():
        if paths[name].read_bytes() != expected_bytes:
            raise JournalWorkflowError(
                f"journal JSON artifact is not canonical: {name}"
            )

    if evidence["journal_id"] != manifest["journal_id"]:
        raise JournalWorkflowError("journal_id lineage mismatch")
    if assembly.get("journal_id") != manifest["journal_id"]:
        raise JournalWorkflowError("assembly journal_id lineage mismatch")
    if evidence["edition_date"] != manifest["edition_date"]:
        raise JournalWorkflowError("edition_date lineage mismatch")
    if assembly.get("edition_date") != manifest["edition_date"]:
        raise JournalWorkflowError("assembly edition_date lineage mismatch")
    if evidence["manifest_sha256"] != manifest["manifest_sha256"]:
        raise JournalWorkflowError("manifest SHA-256 lineage mismatch")
    if assembly.get("manifest_sha256") != manifest["manifest_sha256"]:
        raise JournalWorkflowError("assembly manifest lineage mismatch")
    if evidence["assembly_sha256"] != assembly["assembly_sha256"]:
        raise JournalWorkflowError("assembly SHA-256 lineage mismatch")

    manifest_case_ids = [
        article["case_id"] for article in manifest["articles"]
    ]
    assembly_case_ids = [
        article["case_id"] for article in assembly["articles"]
    ]
    if evidence["selected_case_ids"] != manifest_case_ids:
        raise JournalWorkflowError("selected article order mismatch")
    if assembly_case_ids != manifest_case_ids:
        raise JournalWorkflowError("assembly article order mismatch")
    if evidence["article_count"] != len(manifest_case_ids):
        raise JournalWorkflowError("verified article_count mismatch")

    pdf_path = paths["journal.pdf"]
    if _sha256_file(pdf_path) != evidence["pdf_sha256"]:
        raise JournalWorkflowError("journal PDF SHA-256 mismatch")
    if pdf_path.stat().st_size != evidence["pdf_byte_count"]:
        raise JournalWorkflowError("journal PDF byte count mismatch")

    try:
        from pypdf import PdfReader

        page_count = len(PdfReader(str(pdf_path)).pages)
    except Exception as exc:
        raise JournalWorkflowError("journal PDF is not structurally readable") from exc
    if page_count != evidence["pdf_page_count"]:
        raise JournalWorkflowError("journal PDF page count mismatch")

    result = deepcopy(evidence)
    result["verification_status"] = "VERIFIED"
    result["verified_directory"] = edition.as_posix()
    return result


def _build_manifest_edition(
    *,
    project_root: Path,
    output_root: Path,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Atomically build an edition from one immutable manifest."""

    validate_finalized_manifest(manifest)
    journal_id = manifest["journal_id"]
    if not JOURNAL_ID_PATTERN.fullmatch(journal_id):
        raise JournalWorkflowError("manifest journal_id is invalid")

    project = project_root.expanduser().resolve()
    output_parent = output_root.expanduser().resolve()
    output_parent.mkdir(parents=True, exist_ok=True)
    target = output_parent / journal_id
    if target.exists():
        raise JournalWorkflowError(
            f"journal edition already exists: {journal_id}"
        )

    assembly = assemble_journal(
        manifest,
        project_root=project,
    )
    validate_assembly(assembly)

    selected_case_ids = [
        article["case_id"] for article in manifest["articles"]
    ]
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{journal_id}.",
            dir=output_parent,
        )
    )

    try:
        manifest_path = temporary / "manifest.json"
        assembly_path = temporary / "assembly.json"
        pdf_path = temporary / "journal.pdf"
        evidence_path = temporary / "build-evidence.json"

        _write_json(manifest_path, manifest)
        _write_json(assembly_path, assembly)
        render_evidence = render_journal_pdf(
            assembly,
            pdf_path,
        )

        evidence: dict[str, Any] = {
            "schema_version": "1.0",
            "journal_id": journal_id,
            "edition_date": manifest["edition_date"],
            "status": "COMPLETE",
            "selected_by": manifest["selected_by"],
            "finalized_at_utc": manifest["finalized_at_utc"],
            "selected_case_ids": selected_case_ids,
            "article_count": manifest["article_count"],
            "manifest_sha256": manifest["manifest_sha256"],
            "assembly_sha256": assembly["assembly_sha256"],
            "pdf_sha256": render_evidence["pdf_sha256"],
            "pdf_page_count": render_evidence["page_count"],
            "pdf_byte_count": render_evidence["byte_count"],
            "renderer_version": render_evidence[
                "renderer_version"
            ],
            "language": "en",
            "tamil_rendered": False,
            "thirukkural_algorithm_usage": "TITLE_ONLY",
            "provider_requests": 0,
            "wordpress_requests": 0,
            "files": {
                "manifest": "manifest.json",
                "assembly": "assembly.json",
                "pdf": "journal.pdf",
                "evidence": "build-evidence.json",
            },
        }
        evidence["evidence_sha256"] = (
            compute_evidence_sha256(evidence)
        )
        validate_build_evidence(evidence)
        _write_json(evidence_path, evidence)
        temporary.rename(target)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    result = deepcopy(evidence)
    result["output_directory"] = target.as_posix()
    return result


def build_weekly_journal(
    *,
    project_root: Path,
    generated_root: Path,
    output_root: Path,
    journal_id: str,
    edition_date: str,
    title: str,
    selected_by: str,
    finalized_at_utc: str,
    case_ids: Sequence[str],
) -> dict[str, Any]:
    """Build one legacy edition from an explicit local selection."""

    if (
        not isinstance(journal_id, str)
        or not JOURNAL_ID_PATTERN.fullmatch(journal_id)
    ):
        raise JournalWorkflowError(
            "journal_id must use uppercase letters, digits, dot, "
            "underscore or hyphen"
        )

    generated = generated_root.expanduser().resolve()
    discovery = discover_articles(generated)
    selected = select_articles(discovery, case_ids)
    manifest = finalize_manifest(
        journal_id=journal_id,
        edition_date=edition_date,
        title=title,
        selected_by=selected_by,
        finalized_at_utc=finalized_at_utc,
        articles=selected,
    )

    return _build_manifest_edition(
        project_root=project_root,
        output_root=output_root,
        manifest=manifest,
    )


def build_finalized_candidate_journal(
    *,
    project_root: Path,
    candidate_storage_root: Path,
    output_root: Path,
    candidate_id: str,
) -> dict[str, Any]:
    """Build directly from a candidate's immutable finalized manifest."""

    try:
        manifest = load_candidate_finalization(
            candidate_storage_root,
            candidate_id,
        )
    except JournalCandidateStoreError as exc:
        raise JournalWorkflowError(
            f"cannot load finalized candidate: {exc}"
        ) from exc

    lineage = manifest.get("candidate_lineage")
    if (
        not isinstance(lineage, Mapping)
        or lineage.get("candidate_id") != candidate_id
    ):
        raise JournalWorkflowError(
            "finalized candidate manifest lineage is invalid"
        )

    result = _build_manifest_edition(
        project_root=project_root,
        output_root=output_root,
        manifest=manifest,
    )
    result["candidate_id"] = lineage["candidate_id"]
    result["candidate_revision_number"] = lineage[
        "revision_number"
    ]
    result["candidate_sha256"] = lineage["candidate_sha256"]
    return result
