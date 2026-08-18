"""Deliberate offline finalization of journal candidate revisions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .candidate_store import (
    JournalCandidateStoreError,
    load_candidate_revision,
    store_candidate_finalization,
)
from .discovery import (
    JournalDiscoveryError,
    discover_articles,
    select_articles,
)
from .manifest import finalize_manifest


class JournalCandidateFinalizationError(ValueError):
    """Raised when an editorial candidate cannot be finalized."""


def _utc_value(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise JournalCandidateFinalizationError(
            "finalized_at_utc must be explicit UTC"
        )
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise JournalCandidateFinalizationError(
            "finalized_at_utc must use ISO-8601 UTC format"
        ) from exc


def finalize_candidate(
    *,
    storage_root: Path,
    generated_root: Path,
    candidate_id: str,
    selected_by: str,
    finalized_at_utc: str,
) -> dict[str, Any]:
    """Revalidate and permanently finalize the latest candidate revision."""

    try:
        candidate = load_candidate_revision(
            storage_root,
            candidate_id,
        )
    except JournalCandidateStoreError as exc:
        raise JournalCandidateFinalizationError(str(exc)) from exc

    finalized_time = _utc_value(finalized_at_utc)
    revised_time = _utc_value(candidate["revised_at_utc"])
    if finalized_time <= revised_time:
        raise JournalCandidateFinalizationError(
            "finalization timestamp must be later than candidate revision"
        )

    selected_case_ids = [
        article["case_id"] for article in candidate["articles"]
    ]

    try:
        discovery = discover_articles(generated_root)
        selected = select_articles(discovery, selected_case_ids)
    except JournalDiscoveryError as exc:
        raise JournalCandidateFinalizationError(
            f"candidate source revalidation failed: {exc}"
        ) from exc

    manifest = finalize_manifest(
        journal_id=candidate["journal_id"],
        edition_date=candidate["edition_date"],
        title=candidate["title"],
        selected_by=selected_by,
        finalized_at_utc=finalized_at_utc,
        articles=selected,
        candidate_lineage={
            "candidate_id": candidate["candidate_id"],
            "revision_number": candidate["revision_number"],
            "candidate_sha256": candidate["candidate_sha256"],
        },
    )

    if manifest["articles"] != candidate["articles"]:
        raise JournalCandidateFinalizationError(
            "candidate source or publication metadata changed"
        )

    try:
        return store_candidate_finalization(
            storage_root,
            manifest,
        )
    except JournalCandidateStoreError as exc:
        raise JournalCandidateFinalizationError(str(exc)) from exc
