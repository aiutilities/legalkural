from pathlib import Path

import pytest

from aidpl.editorial_review_worker import (
    decode_live_review,
    validate_article,
)


def valid_article() -> str:
    body = " ".join(["word"] * 650)

    return f"""# Title

Publication status: Draft.

This is not an authentic Thirukkural verse.

## Case Snapshot

{body}

## What Is the Case About?

Details.

## How the Judge Reasoned

Details.

## The Decision

Details.

## Editorial Disclaimer

This is not personalised legal advice.
Founder authorisation is required.
"""


def test_decode_live_review() -> None:
    reviewed = decode_live_review(
        {
            "article_markdown": valid_article(),
            "review_status": "COMPLETE",
            "changes_made": [],
            "uncertainties": [],
            "legal_fidelity_notes": [],
            "editorial_notes": [],
        }
    )

    assert reviewed["review_summary"]["status"] == "COMPLETE"


def test_validate_article_passes() -> None:
    assert validate_article(valid_article()) == []


def test_validate_article_rejects_short_draft() -> None:
    blockers = validate_article("# Short")
    assert blockers


def test_live_authorization_boundary() -> None:
    from aidpl.editorial_review_worker import run_review

    with pytest.raises(
        ValueError,
        match="Live inference is disabled",
    ):
        run_review(
            case_id="LK-TEST",
            case_root=Path("/tmp/not-needed"),
            provider_name="openai",
            allow_live=False,
        )


def test_normalize_article_structure() -> None:
    from aidpl.editorial_review_worker import (
        normalize_article_structure,
    )

    article = (
        "## Case Overview\n\n"
        "A concise case account.\n\n"
        "## Judicial Reasoning\n\n"
        "The Court applied the law.\n\n"
        "## Outcome\n\n"
        "The petition was allowed.\n\n"
        "## Disclaimer\n\n"
        "Draft only.\n"
    )

    normalized = normalize_article_structure(
        article,
        "Fallback Title",
    )

    assert normalized.startswith("# Fallback Title")
    assert "Publication status" in normalized
    assert "## Case Snapshot" in normalized
    assert "## What Is the Case About?" in normalized
    assert "## How the Judge Reasoned" in normalized
    assert "## The Decision" in normalized
    assert "## Editorial Disclaimer" in normalized
    assert "not an authentic" in normalized.lower()
    assert "not personalised legal advice" in normalized.lower()
