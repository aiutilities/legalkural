import json
from pathlib import Path

import pytest

from aidpl.law_review_worker import (
    decode_live_review,
    run_review,
)


def create_case(root: Path) -> None:
    output = root / "output"

    artifacts = {
        "03-facts/facts.json": {
            "material_facts": [],
        },
        "04-issues/issues.json": {
            "issues": [],
        },
        "06-law/law.json": {
            "schema_version": "1.0",
            "reference_case_id": "LK-TEST",
            "status": "REQUIRES_MODEL_REVIEW",
            "constitutional_provisions": [],
            "statutes": [],
            "regulations": [],
            "notifications": [],
            "precedents": [],
            "legal_doctrines": [],
            "ratio_candidates": [],
            "obiter_candidates": [],
            "source_traceability": [],
            "quality_notes": [],
        },
    }

    for relative, payload in artifacts.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    working = root / "working"
    working.mkdir(parents=True)
    (working / "source-text.txt").write_text(
        "<PAGE:1>\nSample judgment.\n</PAGE:1>\n",
        encoding="utf-8",
    )


def test_decode_live_review() -> None:
    transport = {
        "law_json": json.dumps({"status": "REVIEWED"}),
        "review_status": "COMPLETE",
        "changes_made": [],
        "uncertainties": [],
    }

    reviewed = decode_live_review(transport)

    assert reviewed["law"]["status"] == "REVIEWED"
    assert reviewed["review_summary"]["status"] == "COMPLETE"


def test_mock_review(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    create_case(case_root)

    root = Path(__file__).resolve().parents[2]

    report = run_review(
        case_id="LK-TEST",
        case_root=case_root,
        schema_root=root / "engine/schemas",
        provider_name="mock",
        max_source_characters=1000,
        allow_live=False,
    )

    assert report["status"] == "COMPLETE_MOCK"
    assert (
        case_root
        / "working/pre-law-model-review/06-law/law.json"
    ).exists()


def test_live_requires_authorization(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    create_case(case_root)

    root = Path(__file__).resolve().parents[2]

    with pytest.raises(ValueError, match="Live inference is disabled"):
        run_review(
            case_id="LK-TEST",
            case_root=case_root,
            schema_root=root / "engine/schemas",
            provider_name="openai",
            max_source_characters=1000,
            allow_live=False,
        )
