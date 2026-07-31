import json
from pathlib import Path

import pytest

from aidpl.reasoning_review_worker import (
    decode_live_review,
    run_review,
)


def create_case(root: Path) -> None:
    output = root / "output"

    artifacts = {
        "03-facts/facts.json": {"material_facts": []},
        "04-issues/issues.json": {"issues": []},
        "06-law/law.json": {"statutes": []},
        "07-reasoning/reasoning.json": {
            "schema_version": "1.0",
            "reference_case_id": "LK-TEST",
            "status": "REQUIRES_MODEL_REVIEW",
            "issues": [],
            "reasoning_steps": [],
            "accepted_arguments": [],
            "rejected_arguments": [],
            "ratio_candidates": [],
            "limitations": [],
            "source_traceability": [],
            "quality_notes": [],
        },
        "08-decision/decision.json": {
            "schema_version": "1.0",
            "reference_case_id": "LK-TEST",
            "status": "REQUIRES_MODEL_REVIEW",
            "outcome": None,
            "operative_directions": [],
            "relief_granted": [],
            "relief_denied": [],
            "costs": None,
            "limitations": [],
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
        "reasoning_json": json.dumps({"status": "REVIEWED"}),
        "decision_json": json.dumps({"status": "REVIEWED"}),
        "review_status": "COMPLETE",
        "changes_made": [],
        "uncertainties": [],
    }

    reviewed = decode_live_review(transport)

    assert reviewed["reasoning"]["status"] == "REVIEWED"
    assert reviewed["decision"]["status"] == "REVIEWED"


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
        / "working/pre-reasoning-model-review/"
        "07-reasoning/reasoning.json"
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


def test_normalize_rich_reasoning_contract() -> None:
    from aidpl.reasoning_review_worker import (
        normalize_reasoning_contract,
    )

    rich = {
        "case_id": "LK-TEST",
        "issues": [
            {
                "issue_no": 1,
                "question": "Whether the classification is valid?",
                "analysis_steps": [
                    {
                        "text": "Actual use determines classification.",
                        "source_pages": [24],
                    }
                ],
                "accepted_arguments": [
                    {
                        "text": "Recipient use is residential.",
                        "source_pages": [25],
                    }
                ],
                "ratio_candidates": [
                    {
                        "text": "Use, not label, governs.",
                        "source_pages": [30],
                    }
                ],
            }
        ],
        "scope_and_limitations": [
            {
                "text": "Verification is required.",
                "source_pages": [53],
            }
        ],
    }

    normalized = normalize_reasoning_contract("LK-TEST", rich)

    assert normalized["schema_version"] == "1.0"
    assert normalized["reference_case_id"] == "LK-TEST"
    assert normalized["reasoning_steps"]
    assert normalized["ratio_candidates"]
    assert normalized["limitations"]


def test_normalize_rich_decision_contract() -> None:
    from aidpl.reasoning_review_worker import (
        normalize_decision_contract,
    )

    rich = {
        "outcome": "Allowed",
        "directions": [
            {
                "text": "The impugned notices are quashed.",
                "source_pages": [53],
            }
        ],
        "costs": "No costs.",
    }

    normalized = normalize_decision_contract(
        "LK-TEST",
        rich,
        {"limitations": []},
    )

    assert normalized["schema_version"] == "1.0"
    assert normalized["outcome"] == "Allowed"
    assert normalized["operative_directions"]
    assert normalized["relief_granted"]
