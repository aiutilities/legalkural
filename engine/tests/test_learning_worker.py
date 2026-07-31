import json
from pathlib import Path

from aidpl.learning_worker import run_learning


def test_run_learning(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    evidence = case_root / "evidence"
    evidence.mkdir(parents=True)

    plan = {
        "agents": [
            {"agent_id": "LK-INTAKE", "status": "COMPLETE"},
            {"agent_id": "LK-QA", "status": "COMPLETE"},
        ]
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan) + "\n", encoding="utf-8")

    (evidence / "validation-report.json").write_text(
        json.dumps(
            {
                "verdict": "REVIEW_REQUIRED",
                "publication_ready": False,
                "checks": [{}, {}],
                "blocking_errors": [],
                "review_reasons": ["model review required"],
            }
        ) + "\n",
        encoding="utf-8",
    )

    (evidence / "editorial-report.json").write_text(
        json.dumps({"word_count": 1200}) + "\n",
        encoding="utf-8",
    )

    report = run_learning(
        case_id="LK-LEARN-TEST-0001",
        case_root=case_root,
        plan_path=plan_path,
    )

    assert report["status"] == "COMPLETE"
    assert report["next_action"] == "MODEL_ASSISTED_REVIEW"
    assert (
        case_root
        / "output/11-learning/thinking-review.md"
    ).exists()
