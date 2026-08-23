import json
from pathlib import Path

from aidpl.kural_worker import (
    build_brief,
    render_markdown,
    run_kural_generation,
)


def sample_artifacts() -> tuple[dict, dict, dict, dict]:
    facts = {
        "material_facts": [
            {
                "text": (
                    "The occupants used the premises for sleeping "
                    "and ordinary daily living."
                ),
                "source_pages": [10],
            }
        ]
    }
    issues = {
        "issues": [
            {
                "question": (
                    "Whether the property was residential or commercial."
                ),
                "source_pages": [20],
            }
        ]
    }
    reasoning = {
        "ratio_candidates": [
            {
                "text": (
                    "This Court is of the considered view that actual use "
                    "must govern classification."
                ),
                "source_pages": [30],
            }
        ],
        "limitations": [],
    }
    decision = {
        "outcome": "Allowed",
        "operative_directions": [
            {
                "text": "The impugned notices are quashed.",
                "source_pages": [40],
            }
        ],
        "limitations": [
            {
                "text": "The ruling applies only to factually similar cases.",
                "source_pages": [41],
            }
        ],
    }
    return facts, issues, reasoning, decision


def test_build_brief() -> None:
    facts, issues, reasoning, decision = sample_artifacts()

    brief = build_brief(
        "LK-TEST-KURAL-0001",
        facts,
        issues,
        reasoning,
        decision,
    )

    assert brief["compressed_title"]
    assert brief["legal_holding"]
    assert brief["universal_principle"]
    assert brief["thirukkural_algorithm_usage"] == "TITLE_ONLY"
    assert brief["tamil_rendered"] is False
    assert "kural_inspired_english" not in brief
    assert "kural_inspired_tamil" not in brief
    assert brief["requires_human_editorial_review"] is True


def test_render_markdown() -> None:
    facts, issues, reasoning, decision = sample_artifacts()

    brief = build_brief(
        "LK-TEST-KURAL-0002",
        facts,
        issues,
        reasoning,
        decision,
    )
    markdown = render_markdown(brief)

    assert "TITLE_ONLY" in markdown
    assert "Tamil rendered: `false`" in markdown
    assert "Kural-Inspired English" not in markdown
    assert "Kural-Inspired Tamil" not in markdown
    assert "Founder approved" in markdown


def test_run_kural_generation(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    output = case_root / "output"

    facts, issues, reasoning, decision = sample_artifacts()

    for directory, filename, payload in [
        ("03-facts", "facts.json", facts),
        ("04-issues", "issues.json", issues),
        ("07-reasoning", "reasoning.json", reasoning),
        ("08-decision", "decision.json", decision),
    ]:
        target = output / directory
        target.mkdir(parents=True, exist_ok=True)
        (target / filename).write_text(
            json.dumps(payload) + "\n",
            encoding="utf-8",
        )

    root = Path(__file__).resolve().parents[2]

    report = run_kural_generation(
        case_id="LK-TEST-KURAL-0003",
        case_root=case_root,
        schema_root=root / "engine/schemas",
    )

    assert report["schema_validation"] == "PASS"
    assert report["tamil_rendered"] is False
    assert report["thirukkural_algorithm_usage"] == "TITLE_ONLY"
    assert (output / "09-kural/kural-brief.json").exists()
    assert (output / "09-kural/kural.md").exists()


def test_derive_holding_prefers_substantive_reviewed_argument_when_ratio_empty():
    from aidpl.kural_worker import derive_holding

    reasoning = {
        "ratio_candidates": [],
        "accepted_arguments": [
            {
                "text": (
                    "Tariff classification must be based on end-use from "
                    "the perspective of the recipient of services; inmates "
                    "use hostel rooms as residences, hence residential "
                    "tariff applies."
                ),
                "status": "MODEL_REVIEWED",
            },
            {
                "text": (
                    "No prior notice was given before reclassification, "
                    "violating principles of natural justice."
                ),
                "status": "MODEL_REVIEWED",
            },
        ],
    }

    decision = {
        "outcome": "Allowed",
        "operative_directions": [
            {
                "text": (
                    "All the impugned demand/recovery notices are quashed."
                )
            }
        ],
    }

    holding = derive_holding(reasoning, decision)

    assert "end-use" in holding
    assert "residential tariff applies" in holding


def test_derive_principle_recognizes_end_use_classification():
    from aidpl.kural_worker import derive_principle

    holding = (
        "Tariff classification must be based on end-use from the "
        "perspective of the recipient; residential use attracts "
        "residential rather than commercial tariff."
    )

    principle = derive_principle(holding, [])

    assert principle == (
        "Legal classification should follow proven functional use, "
        "not merely the label or commercial identity attached to it."
    )
