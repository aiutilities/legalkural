"""Deterministic weekly-journal manifest contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
import re
from typing import Any


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class JournalManifestError(ValueError):
    """Raised when a weekly-journal manifest violates its contract."""


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Serialize a mapping using the canonical LegalKural JSON form."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_manifest_sha256(manifest: Mapping[str, Any]) -> str:
    """Hash a manifest without including its self-referential digest."""

    payload = deepcopy(dict(manifest))
    payload.pop("manifest_sha256", None)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JournalManifestError(f"{field} must be a non-empty string")
    return value.strip()


def _iso_date(value: Any, field: str) -> str:
    text = _required_text(value, field)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise JournalManifestError(
            f"{field} must use YYYY-MM-DD format"
        ) from exc
    return text


def _utc_datetime(value: Any, field: str) -> str:
    text = _required_text(value, field)

    if not text.endswith("Z"):
        raise JournalManifestError(f"{field} must be an explicit UTC value")

    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise JournalManifestError(
            f"{field} must use ISO-8601 UTC format"
        ) from exc

    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise JournalManifestError(f"{field} must be UTC")

    return text


def _sha256(value: Any, field: str) -> str:
    text = _required_text(value, field)
    if not SHA256_PATTERN.fullmatch(text):
        raise JournalManifestError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return text


def _normalize_articles(
    articles: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(articles, (str, bytes)) or not isinstance(articles, Sequence):
        raise JournalManifestError("articles must be a sequence")

    if not articles:
        raise JournalManifestError("at least one article must be selected")

    normalized: list[dict[str, Any]] = []
    seen_case_ids: set[str] = set()
    seen_content_hashes: set[str] = set()

    for expected_position, source in enumerate(articles, start=1):
        if not isinstance(source, Mapping):
            raise JournalManifestError("each article must be an object")

        case_id = _required_text(source.get("case_id"), "article.case_id")
        title = _required_text(source.get("title"), "article.title")
        slug = _required_text(source.get("slug"), "article.slug")
        source_payload = _required_text(
            source.get("source_payload"),
            "article.source_payload",
        )
        content_sha256 = _sha256(
            source.get("content_sha256"),
            "article.content_sha256",
        )

        if not SLUG_PATTERN.fullmatch(slug):
            raise JournalManifestError(
                "article.slug must be a lowercase hyphenated slug"
            )

        if case_id in seen_case_ids:
            raise JournalManifestError(
                f"duplicate case_id selected: {case_id}"
            )

        if content_sha256 in seen_content_hashes:
            raise JournalManifestError(
                f"duplicate article content selected: {content_sha256}"
            )

        seen_case_ids.add(case_id)
        seen_content_hashes.add(content_sha256)

        normalized.append(
            {
                "position": expected_position,
                "case_id": case_id,
                "title": title,
                "slug": slug,
                "source_payload": source_payload,
                "content_sha256": content_sha256,
            }
        )

    return normalized


def finalize_manifest(
    *,
    journal_id: str,
    edition_date: str,
    title: str,
    selected_by: str,
    finalized_at_utc: str,
    articles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Create an immutable, hashed weekly-journal manifest."""

    normalized_id = _required_text(journal_id, "journal_id")
    normalized_date = _iso_date(edition_date, "edition_date")
    normalized_title = _required_text(title, "title")
    normalized_selector = _required_text(selected_by, "selected_by")
    normalized_time = _utc_datetime(finalized_at_utc, "finalized_at_utc")

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "journal_id": normalized_id,
        "edition_date": normalized_date,
        "title": normalized_title,
        "language": "en",
        "selection_status": "FINALIZED",
        "selected_by": normalized_selector,
        "finalized_at_utc": normalized_time,
        "articles": _normalize_articles(articles),
    }
    manifest["manifest_sha256"] = compute_manifest_sha256(manifest)

    validate_finalized_manifest(manifest)
    return manifest


def validate_finalized_manifest(
    manifest: Mapping[str, Any],
) -> None:
    """Validate structure, ordering, uniqueness and manifest integrity."""

    if not isinstance(manifest, Mapping):
        raise JournalManifestError("manifest must be an object")

    if manifest.get("schema_version") != "1.0":
        raise JournalManifestError("unsupported schema_version")

    if manifest.get("language") != "en":
        raise JournalManifestError(
            "Sprint 56 journal language must be English"
        )

    if manifest.get("selection_status") != "FINALIZED":
        raise JournalManifestError(
            "journal selection must be FINALIZED"
        )

    _required_text(manifest.get("journal_id"), "journal_id")
    _iso_date(manifest.get("edition_date"), "edition_date")
    _required_text(manifest.get("title"), "title")
    _required_text(manifest.get("selected_by"), "selected_by")
    _utc_datetime(manifest.get("finalized_at_utc"), "finalized_at_utc")

    articles = manifest.get("articles")
    normalized_articles = _normalize_articles(articles)

    if list(articles) != normalized_articles:
        raise JournalManifestError(
            "articles must use normalized contiguous positions"
        )

    supplied_digest = _sha256(
        manifest.get("manifest_sha256"),
        "manifest_sha256",
    )
    expected_digest = compute_manifest_sha256(manifest)

    if supplied_digest != expected_digest:
        raise JournalManifestError("manifest_sha256 does not match content")
