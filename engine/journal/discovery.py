"""Offline discovery of certified, published LegalKural articles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class JournalDiscoveryError(ValueError):
    """Raised when discovery or editor selection is invalid."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise JournalDiscoveryError(
            f"cannot read valid JSON: {path}"
        ) from exc

    if not isinstance(payload, dict):
        raise JournalDiscoveryError(f"JSON root must be an object: {path}")

    return payload


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _relative_path(path: Path, generated_root: Path) -> str:
    try:
        return path.relative_to(generated_root.parent).as_posix()
    except ValueError:
        return path.as_posix()


def _normalized_positive_ids(value: Any) -> list[int] | None:
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
        return None
    return sorted(value)


def inspect_case(
    case_root: Path,
    generated_root: Path,
) -> dict[str, Any]:
    """Inspect one case without performing any external request."""

    case_id = case_root.name
    qa_path = case_root / "evidence" / "validation-report.json"
    publication_root = case_root / "output" / "11-publication"
    payload_path = publication_root / "wordpress-final-draft-payload.json"
    evidence_path = publication_root / "wordpress-publication-evidence.json"

    required = {
        "qa_report": qa_path,
        "final_payload": payload_path,
        "publication_evidence": evidence_path,
    }
    missing = [
        name
        for name, path in required.items()
        if not path.is_file()
    ]

    if missing:
        return {
            "case_id": case_id,
            "eligible": False,
            "reasons": [
                f"missing required artifact: {name}"
                for name in missing
            ],
        }

    try:
        qa = _read_json(qa_path)
        payload = _read_json(payload_path)
        evidence = _read_json(evidence_path)
    except JournalDiscoveryError as exc:
        return {
            "case_id": case_id,
            "eligible": False,
            "reasons": [str(exc)],
        }

    reasons: list[str] = []

    if qa.get("verdict") != "PASS":
        reasons.append("QA verdict is not PASS")

    if qa.get("publication_ready") is not True:
        reasons.append("QA publication_ready is not true")

    if evidence.get("case_id") != case_id:
        reasons.append("publication evidence case_id mismatch")

    if evidence.get("status") != "publish":
        reasons.append("publication evidence status is not publish")

    if evidence.get("publication_performed") is not True:
        reasons.append("publication_performed is not true")

    post_id = evidence.get("post_id")
    if not isinstance(post_id, int) or isinstance(post_id, bool) or post_id <= 0:
        reasons.append("publication evidence post_id is invalid")

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        reasons.append("final payload title is missing")

    slug = payload.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        reasons.append("final payload slug is missing")
    elif slug != evidence.get("slug"):
        reasons.append("payload and publication slugs differ")

    content = payload.get("content")
    if not isinstance(content, str) or not content.strip():
        reasons.append("final payload content is missing")
        calculated_content_hash = None
    else:
        calculated_content_hash = _sha256_bytes(content.encode("utf-8"))

    evidence_content_hash = evidence.get("content_hash")
    if (
        not isinstance(evidence_content_hash, str)
        or not SHA256_PATTERN.fullmatch(evidence_content_hash)
    ):
        reasons.append("publication content_hash is invalid")
    elif (
        calculated_content_hash is not None
        and calculated_content_hash != evidence_content_hash
    ):
        reasons.append("published content hash differs from final payload")

    link = evidence.get("link")
    if not isinstance(link, str) or not link.startswith("https://"):
        reasons.append("published HTTPS link is missing")

    published_at = evidence.get("published_at")
    if not isinstance(published_at, str) or not published_at.strip():
        reasons.append("publication timestamp is missing")
    else:
        try:
            datetime.fromisoformat(
                published_at.strip().replace("Z", "+00:00")
            )
        except ValueError:
            reasons.append("publication timestamp is invalid")

    author = evidence.get("author")
    if (
        not isinstance(author, int)
        or isinstance(author, bool)
        or author <= 0
    ):
        reasons.append("publication author is invalid")
    elif payload.get("author") != author:
        reasons.append("payload and publication authors differ")

    categories = _normalized_positive_ids(evidence.get("categories"))
    payload_categories = _normalized_positive_ids(
        payload.get("categories")
    )
    if categories is None:
        reasons.append("publication categories are invalid")
    elif payload_categories != categories:
        reasons.append("payload and publication categories differ")

    tags = _normalized_positive_ids(evidence.get("tags"))
    payload_tags = _normalized_positive_ids(payload.get("tags"))
    if tags is None:
        reasons.append("publication tags are invalid")
    elif payload_tags != tags:
        reasons.append("payload and publication tags differ")

    if reasons:
        return {
            "case_id": case_id,
            "eligible": False,
            "reasons": reasons,
        }

    return {
        "case_id": case_id,
        "eligible": True,
        "title": title.strip(),
        "slug": slug.strip(),
        "source_payload": _relative_path(payload_path, generated_root),
        "content_sha256": evidence_content_hash,
        "publication_evidence": _relative_path(
            evidence_path,
            generated_root,
        ),
        "publication_evidence_sha256": _sha256_file(evidence_path),
        "post_id": post_id,
        "published_url": link,
        "published_at": published_at.strip(),
        "author": author,
        "categories": categories,
        "tags": tags,
    }


def discover_articles(generated_root: Path) -> dict[str, Any]:
    """Discover eligible candidates in stable case-ID order."""

    root = generated_root.expanduser().resolve()

    if not root.is_dir():
        raise JournalDiscoveryError(
            f"generated root does not exist: {generated_root}"
        )

    inspected = [
        inspect_case(case_root, root)
        for case_root in sorted(
            (
                path
                for path in root.iterdir()
                if path.is_dir() and path.name.startswith("LK-")
            ),
            key=lambda path: path.name,
        )
    ]

    return {
        "schema_version": "1.0",
        "generated_root": root.as_posix(),
        "eligible": [
            item for item in inspected if item["eligible"] is True
        ],
        "rejected": [
            item for item in inspected if item["eligible"] is False
        ],
    }


def select_articles(
    discovery: Mapping[str, Any],
    case_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Apply an explicit editor-selected order to discovered candidates."""

    if isinstance(case_ids, (str, bytes)) or not isinstance(
        case_ids,
        Sequence,
    ):
        raise JournalDiscoveryError("case_ids must be a sequence")

    normalized = []
    for value in case_ids:
        if not isinstance(value, str) or not value.strip():
            raise JournalDiscoveryError(
                "every selected case_id must be non-empty"
            )
        normalized.append(value.strip())

    if not normalized:
        raise JournalDiscoveryError(
            "the editor must select at least one article"
        )

    if len(normalized) != len(set(normalized)):
        raise JournalDiscoveryError(
            "the editor selection contains duplicate case_ids"
        )

    eligible = discovery.get("eligible")
    if not isinstance(eligible, list):
        raise JournalDiscoveryError(
            "discovery report has no eligible candidate list"
        )

    indexed = {
        item.get("case_id"): item
        for item in eligible
        if isinstance(item, Mapping)
        and isinstance(item.get("case_id"), str)
    }

    missing = [case_id for case_id in normalized if case_id not in indexed]
    if missing:
        raise JournalDiscoveryError(
            "selected case_ids are not eligible: " + ", ".join(missing)
        )

    selected: list[dict[str, Any]] = []
    for case_id in normalized:
        candidate = indexed[case_id]
        selected.append(
            {
                "case_id": candidate["case_id"],
                "title": candidate["title"],
                "slug": candidate["slug"],
                "source_payload": candidate["source_payload"],
                "content_sha256": candidate["content_sha256"],
                "publication_evidence": candidate[
                    "publication_evidence"
                ],
                "publication_evidence_sha256": candidate[
                    "publication_evidence_sha256"
                ],
                "published_url": candidate["published_url"],
                "published_at": candidate["published_at"],
                "author": candidate["author"],
                "categories": list(candidate["categories"]),
                "tags": list(candidate["tags"]),
            }
        )

    return selected
