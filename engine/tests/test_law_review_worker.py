import json
from pathlib import Path

import pytest

from jsonschema import ValidationError, validate

from aidpl.law_review_worker import (
    canonicalize_law_contract,
    decode_live_review,
    run_review,
    build_prompt,
    guard_against_destructive_law_collapse,
    substantive_law_count,
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


def test_canonicalize_law_contract_flattens_authorities() -> None:
    payload = {
        "status": "draft",
        "case_id": "MODEL-CASE",
        "authorities": {
            "constitutional_provisions": [{"provision": "Article 14"}],
            "statutes": [{"name": "Sample Act"}],
            "regulations": [],
            "notifications": [],
            "precedents": [],
            "legal_doctrines": [],
        },
        "constitutional_provisions": [{"provision": "Article 14"}],
        "statutes": [{"name": "Sample Act"}],
        "source_traceability": [
            {
                "category": "constitutional_provisions",
                "source_pages": [1],
            }
        ],
        "disposition_summary": {"outcome": "Allowed"},
        "traceability_notes": ["Provider commentary."],
    }

    normalized = canonicalize_law_contract(
        "LK-TEST",
        payload,
    )

    assert normalized["schema_version"] == "1.0"
    assert normalized["reference_case_id"] == "MODEL-CASE"
    assert normalized["status"] == "MODEL_REVIEWED_LIVE"

    assert normalized["constitutional_provisions"] == [
        {"provision": "Article 14"}
    ]
    assert normalized["statutes"] == [{"name": "Sample Act"}]

    assert "authorities" not in normalized
    assert "case_id" not in normalized
    assert "disposition_summary" not in normalized
    assert "traceability_notes" not in normalized


def test_canonicalize_law_contract_uses_nested_family_when_top_missing() -> None:
    payload = {
        "authorities": {
            "constitutional_provisions": [],
            "statutes": [{"name": "Nested Act"}],
            "regulations": [],
            "notifications": [],
            "precedents": [],
            "legal_doctrines": [],
        },
        "source_traceability": [],
    }

    normalized = canonicalize_law_contract(
        "LK-TEST",
        payload,
    )

    assert normalized["statutes"] == [{"name": "Nested Act"}]
    assert "authorities" not in normalized


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


def test_law_schema_rejects_duplicate_authorities_container() -> None:
    root = Path(__file__).resolve().parents[2]
    schema = json.loads(
        (root / "engine/schemas/law.schema.json").read_text(
            encoding="utf-8"
        )
    )

    artifact = {
        "schema_version": "1.0",
        "reference_case_id": "LK-TEST",
        "status": "MODEL_REVIEWED_LIVE",
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
        "authorities": {
            "constitutional_provisions": [],
            "statutes": [],
        },
    }

    with pytest.raises(ValidationError):
        validate(instance=artifact, schema=schema)


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


def test_b11_r2_prompt_preserves_impossible_source_citation():
    system_prompt, _ = build_prompt(
        "LK-TEST",
        "The discrimination violates Articles 14 and 19(1)(8).",
        {},
        {},
        {},
    )

    normalized = " ".join(system_prompt.split())

    assert "SOURCE ANOMALIES" in system_prompt
    assert "silently correct" in normalized
    assert "source-recorded constitutional provision" in normalized
    assert "legally plausible alternative" in normalized
    assert "obiter" in normalized
    assert "ratio" in normalized


def test_b11_r4_r2_canonicalization_rejects_unrecognized_payload() -> None:
    payload = {
        "schema_version": "1.0",
        "reference_case_id": "LK-TEST",
        "status": "REVIEWED_CONSOLIDATED",
        "review_summary": {
            "status": "REVIEWED_CONSOLIDATED",
        },
    }

    with pytest.raises(
        ValueError,
        match="no recognized substantive law artifact lists",
    ):
        canonicalize_law_contract(
            "LK-TEST",
            payload,
        )


def test_b11_r4_r2_canonicalization_accepts_explicit_empty_contract() -> None:
    payload = {
        "schema_version": "1.0",
        "reference_case_id": "LK-TEST",
        "constitutional_provisions": [],
        "statutes": [],
        "regulations": [],
        "notifications": [],
        "precedents": [],
        "legal_doctrines": [],
        "ratio_candidates": [],
        "obiter_candidates": [],
        "quality_notes": [],
        "source_traceability": [],
    }

    normalized = canonicalize_law_contract(
        "LK-TEST",
        payload,
    )

    assert normalized["reference_case_id"] == "LK-TEST"
    assert normalized["status"] == "MODEL_REVIEWED_LIVE"
    assert normalized["constitutional_provisions"] == []
    assert normalized["ratio_candidates"] == []


def test_b11_r4_r2_canonicalization_preserves_source_anomaly() -> None:
    payload = {
        "schema_version": "1.0",
        "reference_case_id": "LK-TEST",
        "constitutional_provisions": [
            {
                "article": (
                    "Article 19(1)(8) "
                    "(as recorded in judgment)"
                ),
                "how_court_used": (
                    "Source-recorded constitutional anomaly."
                ),
                "pages": [27],
                "treatment": "discussed",
            }
        ],
        "statutes": [],
        "regulations": [],
        "notifications": [],
        "precedents": [],
        "legal_doctrines": [],
        "ratio_candidates": [],
        "obiter_candidates": [],
        "quality_notes": [
            "Article 19(1)(8) is preserved as a SOURCE ANOMALY."
        ],
        "source_traceability": [],
    }

    normalized = canonicalize_law_contract(
        "LK-TEST",
        payload,
    )

    assert len(normalized["constitutional_provisions"]) == 1
    assert (
        normalized["constitutional_provisions"][0]["article"]
        == "Article 19(1)(8) (as recorded in judgment)"
    )
    assert "SOURCE ANOMALY" in normalized["quality_notes"][0]

def test_b11_r4_r3_substantive_law_count() -> None:
    payload = {
        "constitutional_provisions": [{"article": "Article 226"}],
        "statutes": [{"name": "Example Act"}],
        "regulations": [],
        "notifications": [],
        "precedents": [],
        "legal_doctrines": [],
        "ratio_candidates": [{"text": "Ratio"}],
        "obiter_candidates": [],
        "source_traceability": [
            {
                "category": "constitutional_provisions",
                "source_pages": [1],
            }
        ],
        "quality_notes": [],
    }

    assert substantive_law_count(payload) == 4


def test_b11_r4_r3_rejects_total_live_collapse() -> None:
    baseline = {
        "constitutional_provisions": [{"article": "Article 226"}],
        "statutes": [{"name": "Example Act"}],
        "regulations": [],
        "notifications": [],
        "precedents": [],
        "legal_doctrines": [],
        "ratio_candidates": [{"text": "Ratio"}],
        "obiter_candidates": [],
        "source_traceability": [
            {
                "category": "constitutional_provisions",
                "source_pages": [1],
            }
        ],
        "quality_notes": [],
    }

    reviewed = {
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
    }

    with pytest.raises(
        ValueError,
        match="destructively collapsed",
    ):
        guard_against_destructive_law_collapse(
            baseline,
            reviewed,
        )


def test_b11_r4_r3_allows_legitimate_substantive_review() -> None:
    baseline = {
        "constitutional_provisions": [{"article": "Article 226"}],
        "statutes": [{"name": "Example Act"}],
        "regulations": [],
        "notifications": [],
        "precedents": [],
        "legal_doctrines": [],
        "ratio_candidates": [{"text": "Old ratio"}],
        "obiter_candidates": [],
        "source_traceability": [],
        "quality_notes": [],
    }

    reviewed = {
        "constitutional_provisions": [
            {
                "article": (
                    "Article 19(1)(8) "
                    "(as recorded in judgment)"
                )
            }
        ],
        "statutes": [],
        "regulations": [],
        "notifications": [],
        "precedents": [],
        "legal_doctrines": [],
        "ratio_candidates": [],
        "obiter_candidates": [
            {
                "text": (
                    "Equality/discrimination observation "
                    "retained as obiter."
                )
            }
        ],
        "source_traceability": [
            {
                "category": "constitutional_provisions",
                "source_pages": [27],
            }
        ],
        "quality_notes": [
            "Article 19(1)(8) preserved as SOURCE ANOMALY."
        ],
    }

    guard_against_destructive_law_collapse(
        baseline,
        reviewed,
    )
