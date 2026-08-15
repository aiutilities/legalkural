from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .orchestrator import (
    find_agent,
    load_plan,
    refresh_readiness,
    save_plan,
)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_post_certification_learning(
    plan: dict[str, Any],
    qa: dict[str, Any],
) -> dict[str, Any]:
    if qa.get("verdict") != "PASS":
        raise ValueError(
            "Post-certification learning requires QA verdict PASS."
        )

    if qa.get("publication_ready") is not True:
        raise ValueError(
            "Post-certification learning requires publication_ready=true."
        )

    if qa.get("next_agent") != "LK-LEARN":
        raise ValueError(
            "Certified QA must designate LK-LEARN as next_agent."
        )

    qa_agent = find_agent(plan, "LK-QA")

    if qa_agent["status"] != "COMPLETE":
        raise ValueError(
            "Post-certification learning requires LK-QA COMPLETE."
        )

    learn = find_agent(plan, "LK-LEARN")

    previous_execution = copy.deepcopy(learn)

    learn["status"] = "PENDING"
    learn["started_at_utc"] = None
    learn["completed_at_utc"] = None
    learn["reviewed_by"] = None
    learn["verdict"] = None
    learn["notes"] = [
        "Fresh post-certification learning iteration prepared."
    ]

    refresh_readiness(plan)

    if learn["status"] != "READY":
        raise ValueError(
            "Fresh LK-LEARN iteration did not become READY."
        )

    return previous_execution


def run_post_certification_learning(
    case_root: Path,
    python_executable: str = sys.executable,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()
    plan_path = case_root / "aidpl-plan.json"
    qa_path = case_root / "evidence/validation-report.json"

    plan = load_plan(plan_path)
    qa = read_json(qa_path)

    previous_execution = prepare_post_certification_learning(
        plan,
        qa,
    )
    save_plan(plan_path, plan)

    command = [
        python_executable,
        "-m",
        "aidpl.learning_worker",
        "--case-id",
        str(plan["case_id"]),
        "--case-root",
        str(case_root),
        "--plan",
        str(plan_path),
    ]

    subprocess.run(command, check=True)

    final_plan = load_plan(plan_path)
    final_learn = find_agent(final_plan, "LK-LEARN")
    report = read_json(
        case_root / "evidence/learning-report.json"
    )

    if final_learn["status"] != "COMPLETE":
        raise ValueError(
            "Post-certification LK-LEARN did not complete."
        )

    if report.get("next_action") != (
        "POST_CERTIFICATION_LEARNING_REVIEW"
    ):
        raise ValueError(
            "Learning report did not preserve "
            "post-certification semantics."
        )

    return {
        "case_id": plan["case_id"],
        "status": "COMPLETE",
        "previous_execution": previous_execution,
        "learning": final_learn,
        "report": report,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-post-certification-learning",
        description=(
            "Run a fresh Legal Kural learning iteration "
            "after certified QA."
        ),
    )
    parser.add_argument(
        "--case-root",
        type=Path,
        required=True,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        result = run_post_certification_learning(
            args.case_root,
        )

        print()
        print("=" * 72)
        print("LEGAL KURAL POST-CERTIFICATION LEARNING")
        print("=" * 72)
        print(f"Case        : {result['case_id']}")
        print(f"Status      : {result['status']}")
        print(
            "Next Action : "
            f"{result['report']['next_action']}"
        )
        print("=" * 72)

        return 0

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
