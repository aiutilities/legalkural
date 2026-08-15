import json
from pathlib import Path

import pytest

from aidpl.kural_review_worker import (
    decode_live_review,
    normalize_kural_contract,
    normalize_legal_holding,
    run_review,
)


def create_case(root: Path) -> None:
    output = root / "output"

    artifacts = {
        "03-facts/facts.json": {"material_facts": []},
        "04-issues/issues.json": {"issues": []},
        "07-reasoning/reasoning.json": {
            "ratio_candidates": [],
        },
        "08-decision/decision.json": {
            "outcome": "Allowed",
        },
        "09-kural/kural-brief.json": {
            "schema_version": "1.0",
            "reference_case_id": "LK-TEST",
            "status": "EDITORIAL_DRAFT_REQUIRES_REVIEW",
            "compressed_title": "Use Reveals Truth",
            "human_conflict": "A conflict.",
            "legal_holding": "A holding.",
            "universal_principle": "A principle.",
            "kural_inspired_english": "Use reveals truth.",
            "kural_inspired_tamil": None,
            "editorial_boundary": "Not authentic Thirukkural.",
            "source_traceability": [],
            "quality_notes": [],
            "requires_human_editorial_review": True,
        },
    }

    for relative, payload in artifacts.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    (output / "09-kural/kural.md").write_text(
        "This is not an authentic Thirukkural verse.\n",
        encoding="utf-8",
    )


def test_decode_live_review() -> None:
    transport = {
        "kural_json": json.dumps({"title": "A title"}),
        "kural_markdown": "Not an authentic Thirukkural verse.",
        "review_status": "COMPLETE",
        "changes_made": [],
        "uncertainties": [],
    }

    reviewed = decode_live_review(transport)

    assert reviewed["kural"]["title"] == "A title"
    assert reviewed["review_summary"]["status"] == "COMPLETE"


def test_normalize_kural_contract() -> None:
    normalized = normalize_kural_contract(
        "LK-TEST",
        {
            "title": "Proof Before Label",
            "conflict": "A conflict.",
            "holding": "A holding.",
            "principle": "A principle.",
            "english_kural": "Proof governs judgment.",
            "tamil_kural": "சான்றே வழி.",
        },
    )

    assert normalized["schema_version"] == "1.0"
    assert normalized["reference_case_id"] == "LK-TEST"
    assert normalized["compressed_title"] == "Proof Before Label"
    assert normalized["requires_human_editorial_review"] is True


def test_mock_review(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    create_case(case_root)

    root = Path(__file__).resolve().parents[2]

    report = run_review(
        case_id="LK-TEST",
        case_root=case_root,
        schema_root=root / "engine/schemas",
        provider_name="mock",
        allow_live=False,
    )

    assert report["status"] == "COMPLETE_MOCK"
    assert (
        case_root
        / "working/pre-kural-model-review/09-kural/kural-brief.json"
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
            allow_live=False,
        )


def test_normalize_legal_holding_flattens_structured_model_output() -> None:
    holding = {
        "classification_and_tariff": (
            "Tariff classification follows residential end-use."
        ),
        "natural_justice_and_maintainability": (
            "Reclassification without notice breached natural justice."
        ),
        "operative_limits": (
            "The directions are confined to the present batch."
        ),
    }

    normalized = normalize_legal_holding(holding)

    assert normalized == (
        "Tariff classification follows residential end-use. "
        "Reclassification without notice breached natural justice. "
        "The directions are confined to the present batch."
    )

    assert "{'" not in normalized
    assert "'classification_and_tariff'" not in normalized


def test_normalize_kural_contract_accepts_structured_legal_holding() -> None:
    normalized = normalize_kural_contract(
        "LK-TEST",
        {
            "compressed_title": "End-Use Over Label",
            "human_conflict": "A tariff classification dispute.",
            "legal_holding": {
                "classification_and_tariff": (
                    "Residential end-use attracts residential tariff."
                ),
                "natural_justice_and_maintainability": (
                    "Reclassification without notice breached natural justice."
                ),
                "operative_limits": (
                    "Similar cases require factual verification."
                ),
            },
            "universal_principle": (
                "Classification should follow proven functional use."
            ),
            "kural_inspired_english": (
                "Use reveals what labels conceal."
            ),
            "kural_inspired_tamil": None,
            "source_traceability": [],
        },
    )

    assert normalized["legal_holding"] == (
        "Residential end-use attracts residential tariff. "
        "Reclassification without notice breached natural justice. "
        "Similar cases require factual verification."
    )

    assert normalized["requires_human_editorial_review"] is True
