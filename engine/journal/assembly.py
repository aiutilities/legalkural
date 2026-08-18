"""Deterministic assembly of finalized LegalKural journal content."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from .manifest import (
    canonical_json_bytes,
    validate_finalized_manifest,
)


class JournalAssemblyError(ValueError):
    """Raised when selected journal content cannot be assembled safely."""


def compute_assembly_sha256(assembly: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(assembly))
    payload.pop("assembly_sha256", None)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise JournalAssemblyError(
            f"cannot read valid source payload: {path}"
        ) from exc

    if not isinstance(payload, dict):
        raise JournalAssemblyError(
            f"source payload root must be an object: {path}"
        )

    return payload


def _safe_source_path(project_root: Path, raw: Any) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise JournalAssemblyError("source_payload must be non-empty")

    root = project_root.expanduser().resolve()
    candidate = (root / raw).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise JournalAssemblyError(
            "source_payload escapes the project root"
        ) from exc

    if not candidate.is_file():
        raise JournalAssemblyError(
            f"source_payload does not exist: {raw}"
        )

    return candidate


def assemble_journal(
    manifest: Mapping[str, Any],
    *,
    project_root: Path,
) -> dict[str, Any]:
    """Assemble selected articles after revalidating every source hash."""

    validate_finalized_manifest(manifest)

    assembled_articles: list[dict[str, Any]] = []

    for selected in manifest["articles"]:
        payload_path = _safe_source_path(
            project_root,
            selected["source_payload"],
        )
        payload = _read_json(payload_path)

        title = payload.get("title")
        slug = payload.get("slug")
        content = payload.get("content")
        excerpt = payload.get("excerpt", "")

        if title != selected["title"]:
            raise JournalAssemblyError(
                f"title mismatch for {selected['case_id']}"
            )

        if slug != selected["slug"]:
            raise JournalAssemblyError(
                f"slug mismatch for {selected['case_id']}"
            )

        if not isinstance(content, str) or not content.strip():
            raise JournalAssemblyError(
                f"content missing for {selected['case_id']}"
            )

        if not isinstance(excerpt, str):
            raise JournalAssemblyError(
                f"excerpt must be text for {selected['case_id']}"
            )

        content_hash = hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

        if content_hash != selected["content_sha256"]:
            raise JournalAssemblyError(
                f"content hash mismatch for {selected['case_id']}"
            )

        assembled_articles.append(
            {
                "position": selected["position"],
                "case_id": selected["case_id"],
                "title": title,
                "slug": slug,
                "excerpt": excerpt,
                "content_html": content,
                "content_sha256": content_hash,
                "source_payload": selected["source_payload"],
                "publication_evidence": selected[
                    "publication_evidence"
                ],
                "publication_evidence_sha256": selected[
                    "publication_evidence_sha256"
                ],
                "published_url": selected["published_url"],
                "published_at": selected["published_at"],
                "author": selected["author"],
                "categories": list(selected["categories"]),
                "tags": list(selected["tags"]),
            }
        )

    assembly: dict[str, Any] = {
        "schema_version": "1.0",
        "journal_id": manifest["journal_id"],
        "edition_date": manifest["edition_date"],
        "covered_date_range": deepcopy(
            manifest["covered_date_range"]
        ),
        "title": manifest["title"],
        "article_count": manifest["article_count"],
        "language": "en",
        "manifest_sha256": manifest["manifest_sha256"],
        "rendering_policy": {
            "body_language": "en",
            "tamil_rendering": False,
            "thirukkural_algorithm_usage": "TITLE_ONLY",
            "website_dressing": "DEFERRED_TO_FINAL_SPRINT",
        },
        "articles": assembled_articles,
    }
    assembly["assembly_sha256"] = compute_assembly_sha256(assembly)

    return assembly


def validate_assembly(assembly: Mapping[str, Any]) -> None:
    """Validate the assembled journal and its integrity digest."""

    if not isinstance(assembly, Mapping):
        raise JournalAssemblyError("assembly must be an object")

    if assembly.get("schema_version") != "1.0":
        raise JournalAssemblyError("unsupported assembly schema_version")

    if assembly.get("language") != "en":
        raise JournalAssemblyError("journal assembly must be English")

    policy = assembly.get("rendering_policy")
    if not isinstance(policy, Mapping):
        raise JournalAssemblyError("rendering_policy is missing")

    if policy.get("tamil_rendering") is not False:
        raise JournalAssemblyError("Tamil rendering must remain disabled")

    if policy.get("thirukkural_algorithm_usage") != "TITLE_ONLY":
        raise JournalAssemblyError(
            "Thirukkural algorithm usage must remain TITLE_ONLY"
        )

    articles = assembly.get("articles")
    if not isinstance(articles, list) or not articles:
        raise JournalAssemblyError(
            "assembly must contain at least one article"
        )

    expected_positions = list(range(1, len(articles) + 1))
    actual_positions = [
        article.get("position")
        for article in articles
        if isinstance(article, Mapping)
    ]

    if actual_positions != expected_positions:
        raise JournalAssemblyError(
            "assembly article positions are not contiguous"
        )

    if assembly.get("article_count") != len(articles):
        raise JournalAssemblyError(
            "assembly article_count does not match articles"
        )
    publication_dates = [
        article.get("published_at", "")[:10]
        for article in articles
    ]
    expected_range = {
        "start": min(publication_dates),
        "end": max(publication_dates),
    }
    if assembly.get("covered_date_range") != expected_range:
        raise JournalAssemblyError(
            "assembly covered_date_range is invalid"
        )
    supplied_hash = assembly.get("assembly_sha256")
    if not isinstance(supplied_hash, str):
        raise JournalAssemblyError("assembly_sha256 is missing")

    if supplied_hash != compute_assembly_sha256(assembly):
        raise JournalAssemblyError(
            "assembly_sha256 does not match content"
        )
