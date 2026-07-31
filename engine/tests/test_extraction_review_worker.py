import json
from pathlib import Path

import pytest

from aidpl.extraction_review_worker import run_review


def create_case(root: Path) -> None:
    output = root / "output"

    artifacts = {
        "01-metadata/metadata.json": {
            "schema_version": "1.0",
            "reference_case_id": "LK-TEST",
            "status": "DRAFT_DETERMINISTIC",
            "court": "Sample Court",
            "judge": None,
            "case_numbers": [],
            "dates": {
                "reserved_on": None,
                "pronounced_on": None,
            },
            "source_traceability": [],
        },
        "02-timeline/timeline.json": {
            "schema_version": "1.0",
            "reference_case_id": "LK-TEST",
            "status": "DRAFT_DETERMINISTIC",
            "events": [],
        },
        "03-facts/facts.json": {
            "schema_version": "1.0",
            "reference_case_id": "LK-TEST",
            "status": "REQUIRES_MODEL_REVIEW",
            "material_facts": [],
            "undisputed_facts": [],
            "disputed_facts": [],
        },
        "04-issues/issues.json": {
            "schema_version": "1.0",
            "reference_case_id": "LK-TEST",
            "status": "REQUIRES_MODEL_REVIEW",
            "issues": [],
        },
        "05-evidence/evidence.json": {
            "schema_version": "1.0",
            "reference_case_id": "LK-TEST",
            "status": "REQUIRES_MODEL_REVIEW",
            "documentary_evidence": [],
            "electronic_evidence": [],
            "missing_evidence": [],
        },
    }

    for relative, payload in artifacts.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload) + "\n",
            encoding="utf-8",
        )

    working = root / "working"
    working.mkdir(parents=True)
    (working / "source-text.txt").write_text(
        "<PAGE:1>\nSample judgment.\n</PAGE:1>\n",
        encoding="utf-8",
    )


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
    assert report["live_inference"] is False
    assert (
        case_root
        / "working/pre-model-review/03-facts/facts.json"
    ).exists()

    reviewed = json.loads(
        (
            case_root
            / "output/03-facts/facts.json"
        ).read_text(encoding="utf-8")
    )
    assert reviewed["status"] == "MODEL_REVIEWED_MOCK"


def test_live_requires_explicit_authorization(tmp_path: Path) -> None:
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
