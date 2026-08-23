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
    assert "## What Is the Case About?" not in normalized
    assert "## How the Judge Reasoned" in normalized
    assert "## The Decision" in normalized
    assert "## Editorial Disclaimer" in normalized
    assert "not an authentic" not in normalized.lower()
    assert "not personalised legal advice" in normalized.lower()


def test_normalizer_does_not_invent_substantive_sections() -> None:
    from aidpl.editorial_review_worker import (
        normalize_article_structure,
    )

    article = """# Test Case

## Case Snapshot

Verified snapshot.

## Editorial Disclaimer

This is not personalised legal advice.
"""

    normalized = normalize_article_structure(
        article,
        "Fallback Title",
    )

    assert "## What Is the Case About?" not in normalized
    assert "## How the Judge Reasoned" not in normalized
    assert "## The Decision" not in normalized

    assert "This section requires editorial confirmation" not in normalized
    assert "The reasoning must be read with the verified reasoning artifact" not in normalized
    assert "The operative result must be verified against the decision artifact" not in normalized

    blockers = validate_article(normalized)

    assert any(
        "## What Is the Case About?" in blocker
        for blocker in blockers
    )
    assert any(
        "## How the Judge Reasoned" in blocker
        for blocker in blockers
    )
    assert any(
        "## The Decision" in blocker
        for blocker in blockers
    )


def test_editor_prompt_requires_canonical_substantive_sections() -> None:
    from aidpl.editorial_review_worker import build_prompt

    system_prompt, _ = build_prompt(
        case_id="LK-TEST",
        metadata={},
        timeline={},
        facts={},
        issues={},
        evidence={},
        law={},
        reasoning={},
        decision={},
        kural={},
        article="# Draft",
    )

    required_sections = [
        "## Case Snapshot",
        "## What Is the Case About?",
        "## How the Judge Reasoned",
        "## The Decision",
        "## Editorial Disclaimer",
    ]

    for section in required_sections:
        assert section in system_prompt

    assert "meaningful content" in system_prompt
    assert "Do not emit placeholder text" in system_prompt
    assert "do not invent the missing substance" in system_prompt
    assert "downstream validator is intentionally fail-closed" in system_prompt


def test_validate_article_rejects_kural_body_content() -> None:
    article = valid_article().replace(
        "## Case Snapshot",
        "## Kural-Inspired English\n\nA simulated verse.\n\n## Case Snapshot",
    )
    assert any("TITLE_ONLY policy violation" in item for item in validate_article(article))
