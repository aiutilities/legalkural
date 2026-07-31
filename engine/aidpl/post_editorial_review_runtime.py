from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKERS = [
    ("LK-QA", "aidpl-qa"),
    ("LK-LEARN", "aidpl-learn"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def reset_from_qa(plan: dict[str, Any]) -> None:
    agents = {
        agent["agent_id"]: agent
        for agent in plan["agents"]
    }

    for agent_id, _ in WORKERS:
        agent = agents[agent_id]
        agent["status"] = "PENDING"
        agent["started_at_utc"] = None
        agent["completed_at_utc"] = None
        agent["reviewed_by"] = None
        agent["verdict"] = None
        agent["notes"].append(
            "Reset after model-assisted editorial review."
        )

    agents["LK-QA"]["status"] = "READY"
    plan["status"] = "ACTIVE"
    plan["publication"]["qa_status"] = "PENDING"
    plan["publication"]["ready"] = False
    plan["updated_at_utc"] = utc_now()


def run_cycle(
    root: Path,
    case_id: str,
    case_root: Path,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()
    plan_path = case_root / "aidpl-plan.json"

    if not (
        case_root
        / "evidence/editorial-model-review-report.json"
    ).exists():
        raise FileNotFoundError(
            "Editorial model review report is required."
        )

    plan = read_json(plan_path)
    reset_from_qa(plan)
    write_json(plan_path, plan)

    execution = []

    for agent_id, worker in WORKERS:
        started = utc_now()

        command = [
            str(root / "bin" / worker),
            "--case-id",
            case_id,
            "--case-root",
            str(case_root),
            "--plan",
            str(plan_path),
        ]

        try:
            subprocess.run(command, cwd=root, check=True)
            status = "COMPLETE"
            error = None
        except subprocess.CalledProcessError as exc:
            status = "FAILED"
            error = f"Command exited with status {exc.returncode}"

        execution.append(
            {
                "agent_id": agent_id,
                "worker": worker,
                "status": status,
                "started_at_utc": started,
                "completed_at_utc": utc_now(),
                "error": error,
            }
        )

        if status == "FAILED":
            break

    final_plan = read_json(plan_path)

    report = {
        "schema_version": "1.0",
        "runtime": "AIDPL Post-Editorial Review Runtime",
        "runtime_version": "0.1.0",
        "case_id": case_id,
        "status": (
            "COMPLETE"
            if all(
                step["status"] == "COMPLETE"
                for step in execution
            )
            else "FAILED"
        ),
        "execution": execution,
        "publication": final_plan["publication"],
        "next_action": (
            "MODEL_ASSISTED_QA_REVIEW"
            if final_plan["publication"]["qa_status"]
            == "REVIEW_REQUIRED"
            else "FOUNDER_AUTHORIZATION"
        ),
    }

    write_json(
        case_root
        / "evidence/post-editorial-review-runtime-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-review-after-editor",
        description="Run QA and LearningOS after editorial review.",
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(__file__).resolve().parents[2]

    try:
        report = run_cycle(
            root=root,
            case_id=args.case_id,
            case_root=args.case_root,
        )
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print()
    print("=" * 76)
    print("LEGAL KURAL POST-EDITORIAL REVIEW ORCHESTRATION")
    print("=" * 76)
    print(f"Case        : {report['case_id']}")
    print(f"Status      : {report['status']}")
    print(f"Agents      : {len(report['execution'])}")
    print(f"QA          : {report['publication']['qa_status']}")
    print(f"Publish     : {report['publication']['ready']}")
    print(f"Next Action : {report['next_action']}")
    print("=" * 76)

    return 0 if report["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
