"""Deterministic editorial candidate revision contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import date, datetime
import hashlib
import re
from typing import Any

from .manifest import canonical_json_bytes


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]+$")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STATES = {"CANDIDATE"}

CANDIDATE_KEYS = {
    "schema_version",
    "candidate_id",
    "revision_number",
    "previous_revision_sha256",
    "journal_id",
    "edition_date",
    "title",
    "editor",
    "created_at_utc",
    "revised_at_utc",
    "status",
    "articles",
    "candidate_sha256",
}


class JournalCandidateError(ValueError):
    """Raised when an editorial candidate revision is invalid."""


def compute_candidate_sha256(candidate: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(candidate))
    payload.pop("candidate_sha256", None)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JournalCandidateError(f"{field} must be non-empty text")
    return value.strip()


def _identifier(value: Any, field: str) -> str:
    text = _text(value, field)
    if not ID_PATTERN.fullmatch(text):
        raise JournalCandidateError(f"{field} is invalid")
    return text


def _slug(value: Any, field: str) -> str:
    text = _text(value, field)
    if not SLUG_PATTERN.fullmatch(text):
        raise JournalCandidateError(
            f"{field} must be a lowercase hyphenated slug"
        )
    return text


def _date(value: Any, field: str) -> str:
    text = _text(value, field)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise JournalCandidateError(
            f"{field} must use YYYY-MM-DD format"
        ) from exc
    return text


def _utc(value: Any, field: str) -> str:
    text = _text(value, field)
    if not text.endswith("Z"):
        raise JournalCandidateError(f"{field} must be explicit UTC")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise JournalCandidateError(
            f"{field} must use ISO-8601 UTC format"
        ) from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise JournalCandidateError(f"{field} must be UTC")
    return text


def _sha256(value: Any, field: str) -> str:
    text = _text(value, field)
    if not SHA256_PATTERN.fullmatch(text):
        raise JournalCandidateError(f"{field} must be a SHA-256 digest")
    return text


def _positive_id(value: Any, field: str) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value <= 0
    ):
        raise JournalCandidateError(f"{field} must be positive")
    return value


def _positive_ids(value: Any, field: str) -> list[int]:
    if (
        not isinstance(value, list)
        or not value
        or any(
            not isinstance(item, int)
            or isinstance(item, bool)
            or item <= 0
            for item in value
        )
        or len(value) != len(set(value))
    ):
        raise JournalCandidateError(
            f"{field} must contain unique positive IDs"
        )
    normalized = sorted(value)
    if value != normalized:
        raise JournalCandidateError(f"{field} must be sorted")
    return normalized


def _normalize_articles(
    articles: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(articles, (str, bytes)) or not isinstance(
        articles,
        Sequence,
    ):
        raise JournalCandidateError("articles must be a sequence")
    if not articles:
        raise JournalCandidateError(
            "candidate must contain at least one article"
        )

    normalized: list[dict[str, Any]] = []
    seen_case_ids: set[str] = set()
    seen_content_hashes: set[str] = set()

    for position, source in enumerate(articles, start=1):
        if not isinstance(source, Mapping):
            raise JournalCandidateError("every article must be an object")

        case_id = _text(source.get("case_id"), "article.case_id")
        content_sha256 = _sha256(
            source.get("content_sha256"),
            "article.content_sha256",
        )
        if case_id in seen_case_ids:
            raise JournalCandidateError(
                f"duplicate selected case_id: {case_id}"
            )
        if content_sha256 in seen_content_hashes:
            raise JournalCandidateError(
                f"duplicate selected content: {content_sha256}"
            )
        seen_case_ids.add(case_id)
        seen_content_hashes.add(content_sha256)

        published_url = _text(
            source.get("published_url"),
            "article.published_url",
        )
        if not published_url.startswith("https://"):
            raise JournalCandidateError(
                "article.published_url must use HTTPS"
            )

        published_at = _text(
            source.get("published_at"),
            "article.published_at",
        )
        try:
            datetime.fromisoformat(
                published_at.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise JournalCandidateError(
                "article.published_at must use ISO-8601"
            ) from exc

        normalized.append(
            {
                "position": position,
                "case_id": case_id,
                "title": _text(source.get("title"), "article.title"),
                "slug": _slug(source.get("slug"), "article.slug"),
                "source_payload": _text(
                    source.get("source_payload"),
                    "article.source_payload",
                ),
                "content_sha256": content_sha256,
                "publication_evidence": _text(
                    source.get("publication_evidence"),
                    "article.publication_evidence",
                ),
                "publication_evidence_sha256": _sha256(
                    source.get("publication_evidence_sha256"),
                    "article.publication_evidence_sha256",
                ),
                "published_url": published_url,
                "published_at": published_at,
                "author": _positive_id(
                    source.get("author"),
                    "article.author",
                ),
                "categories": _positive_ids(
                    source.get("categories"),
                    "article.categories",
                ),
                "tags": _positive_ids(
                    source.get("tags"),
                    "article.tags",
                ),
            }
        )

    return normalized


def create_candidate_revision(
    *,
    candidate_id: str,
    journal_id: str,
    edition_date: str,
    title: str,
    editor: str,
    revised_at_utc: str,
    articles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_time = _utc(revised_at_utc, "revised_at_utc")
    candidate: dict[str, Any] = {
        "schema_version": "1.0",
        "candidate_id": _identifier(candidate_id, "candidate_id"),
        "revision_number": 1,
        "previous_revision_sha256": None,
        "journal_id": _identifier(journal_id, "journal_id"),
        "edition_date": _date(edition_date, "edition_date"),
        "title": _text(title, "title"),
        "editor": _text(editor, "editor"),
        "created_at_utc": normalized_time,
        "revised_at_utc": normalized_time,
        "status": "CANDIDATE",
        "articles": _normalize_articles(articles),
    }
    candidate["candidate_sha256"] = compute_candidate_sha256(candidate)
    validate_candidate_revision(candidate)
    return candidate


def revise_candidate(
    previous: Mapping[str, Any],
    *,
    revised_at_utc: str,
    articles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    validate_candidate_revision(previous)
    revised_time = _utc(revised_at_utc, "revised_at_utc")
    previous_time = _utc(
        previous.get("revised_at_utc"),
        "previous.revised_at_utc",
    )
    if revised_time <= previous_time:
        raise JournalCandidateError(
            "new revision timestamp must be later"
        )

    revision: dict[str, Any] = {
        "schema_version": "1.0",
        "candidate_id": previous["candidate_id"],
        "revision_number": previous["revision_number"] + 1,
        "previous_revision_sha256": previous["candidate_sha256"],
        "journal_id": previous["journal_id"],
        "edition_date": previous["edition_date"],
        "title": previous["title"],
        "editor": previous["editor"],
        "created_at_utc": previous["created_at_utc"],
        "revised_at_utc": revised_time,
        "status": "CANDIDATE",
        "articles": _normalize_articles(articles),
    }
    revision["candidate_sha256"] = compute_candidate_sha256(revision)
    validate_candidate_revision(revision)
    return revision


def validate_candidate_revision(candidate: Mapping[str, Any]) -> None:
    if not isinstance(candidate, Mapping):
        raise JournalCandidateError("candidate must be an object")
    if set(candidate) != CANDIDATE_KEYS:
        raise JournalCandidateError(
            "candidate fields do not match the runtime contract"
        )
    if candidate.get("schema_version") != "1.0":
        raise JournalCandidateError("unsupported candidate schema")
    if candidate.get("status") not in STATES:
        raise JournalCandidateError("candidate status is invalid")

    _identifier(candidate.get("candidate_id"), "candidate_id")
    _identifier(candidate.get("journal_id"), "journal_id")
    _date(candidate.get("edition_date"), "edition_date")
    _text(candidate.get("title"), "title")
    _text(candidate.get("editor"), "editor")
    _utc(candidate.get("created_at_utc"), "created_at_utc")
    _utc(candidate.get("revised_at_utc"), "revised_at_utc")

    revision_number = candidate.get("revision_number")
    if (
        not isinstance(revision_number, int)
        or isinstance(revision_number, bool)
        or revision_number < 1
    ):
        raise JournalCandidateError("revision_number is invalid")

    previous_hash = candidate.get("previous_revision_sha256")
    if revision_number == 1:
        if previous_hash is not None:
            raise JournalCandidateError(
                "first revision cannot have a previous hash"
            )
        if candidate.get("created_at_utc") != candidate.get(
            "revised_at_utc"
        ):
            raise JournalCandidateError(
                "first revision timestamps must match"
            )
    else:
        _sha256(previous_hash, "previous_revision_sha256")

    articles = candidate.get("articles")
    normalized = _normalize_articles(articles)
    if list(articles) != normalized:
        raise JournalCandidateError(
            "candidate articles are not normalized"
        )

    supplied = _sha256(
        candidate.get("candidate_sha256"),
        "candidate_sha256",
    )
    expected = compute_candidate_sha256(candidate)
    if supplied != expected:
        raise JournalCandidateError(
            "candidate_sha256 does not match content"
        )
