from pathlib import Path

from aidpl.reasoning_worker import (
    build_decision,
    build_reasoning,
    run_reasoning_analysis,
)


def sample_pages() -> list[dict]:
    return [
        {
            "page": 1,
            "text": (
                "Whether the property should be treated as commercial? "
                "In view of the above, this Court is of the considered "
                "view that actual use must govern classification."
            ),
        },
        {
            "page": 2,
            "text": (
                "The contention of the respondent cannot be accepted. "
                "Accordingly, the impugned notices are quashed. "
                "The writ petitions are allowed. No costs. "
                "This order is applicable only to the present cases."
            ),
        },
    ]


def test_build_reasoning() -> None:
    reasoning = build_reasoning(
        case_id="LK-TEST-REASON-0001",
        pages=sample_pages(),
        facts={"material_facts": [{"text": "Sample fact"}]},
        issues={
            "issues": [
                {
                    "question": (
                        "Whether the property should be treated "
                        "as commercial?"
                    ),
                    "source_pages": [1],
                }
            ]
        },
        law={
            "ratio_candidates": [],
            "statutes": [],
            "constitutional_provisions": [],
            "regulations": [],
            "notifications": [],
            "precedents": [],
        },
    )

    assert reasoning["issues"]
    assert reasoning["reasoning_steps"]
    assert reasoning["ratio_candidates"]


def test_build_decision() -> None:
    reasoning = {
        "limitations": [
            {
                "text": "Applicable only to the present cases.",
                "source_pages": [2],
            }
        ]
    }

    decision = build_decision(
        case_id="LK-TEST-REASON-0002",
        pages=sample_pages(),
        reasoning=reasoning,
    )

    assert decision["outcome"] == "Allowed"
    assert decision["operative_directions"]
    assert decision["relief_granted"]
    assert decision["costs"] == "No order as to costs."


def test_run_reasoning_analysis(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    working = case_root / "working"
    output = case_root / "output"

    working.mkdir(parents=True)
    (output / "03-facts").mkdir(parents=True)
    (output / "04-issues").mkdir(parents=True)
    (output / "06-law").mkdir(parents=True)

    source_text = "\n\n".join(
        [
            f"<PAGE:{page['page']}>\n{page['text']}\n"
            f"</PAGE:{page['page']}>"
            for page in sample_pages()
        ]
    )
    (working / "source-text.txt").write_text(
        source_text + "\n",
        encoding="utf-8",
    )

    (output / "03-facts/facts.json").write_text(
        '{"material_facts": []}\n',
        encoding="utf-8",
    )
    (output / "04-issues/issues.json").write_text(
        '{"issues": [{"question": "Sample issue", "source_pages": [1]}]}\n',
        encoding="utf-8",
    )
    (output / "06-law/law.json").write_text(
        '{"ratio_candidates": [], "statutes": [], '
        '"constitutional_provisions": [], "regulations": [], '
        '"notifications": [], "precedents": []}\n',
        encoding="utf-8",
    )

    root = Path(__file__).resolve().parents[2]

    report = run_reasoning_analysis(
        case_id="LK-TEST-REASON-0003",
        case_root=case_root,
        schema_root=root / "engine/schemas",
    )

    assert report["schema_validation"]["reasoning.schema.json"] == "PASS"
    assert report["schema_validation"]["decision.schema.json"] == "PASS"
    assert (case_root / "output/07-reasoning/reasoning.json").exists()
    assert (case_root / "output/08-decision/decision.json").exists()
