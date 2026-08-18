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


def validate_build_evidence(evidence: Mapping[str, Any]) -> None:
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
    """Build one journal edition atomically from local certified artifacts."""

    if not isinstance(journal_id, str) or not JOURNAL_ID_PATTERN.fullmatch(
        journal_id
    ):
        raise JournalWorkflowError(
            "journal_id must use uppercase letters, digits, dot, "
            "underscore or hyphen"
        )

    project = project_root.expanduser().resolve()
    generated = generated_root.expanduser().resolve()
    output_parent = output_root.expanduser().resolve()
    output_parent.mkdir(parents=True, exist_ok=True)

    target = output_parent / journal_id

    if target.exists():
        raise JournalWorkflowError(
            f"journal edition already exists: {journal_id}"
        )

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
    validate_finalized_manifest(manifest)

    assembly = assemble_journal(
        manifest,
        project_root=project,
    )
    validate_assembly(assembly)

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
            "edition_date": edition_date,
            "status": "COMPLETE",
            "selected_by": selected_by,
            "finalized_at_utc": finalized_at_utc,
            "selected_case_ids": list(case_ids),
            "article_count": len(selected),
            "manifest_sha256": manifest["manifest_sha256"],
            "assembly_sha256": assembly["assembly_sha256"],
            "pdf_sha256": render_evidence["pdf_sha256"],
            "pdf_page_count": render_evidence["page_count"],
            "pdf_byte_count": render_evidence["byte_count"],
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
        evidence["evidence_sha256"] = compute_evidence_sha256(evidence)
        validate_build_evidence(evidence)
        _write_json(evidence_path, evidence)

        temporary.rename(target)

    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    result = deepcopy(evidence)
    result["output_directory"] = target.as_posix()
    return result
