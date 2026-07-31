from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGE_ORDER = [
    "LK-EXTRACT",
    "LK-LAW",
    "LK-REASON",
    "LK-KURAL",
    "LK-EDITOR",
    "LK-QA",
]

KEYWORDS = {
    "LK-EXTRACT": [
        "metadata", "timeline", "fact", "evidence", "party",
        "date", "source page", "traceability",
    ],
    "LK-LAW": [
        "statute", "section", "regulation", "notification",
        "precedent", "doctrine", "authority",
        "article 14", "article 19", "article 226",
    ],
    "LK-REASON": [
        "reasoning", "ratio", "obiter", "holding", "finding",
        "decision", "relief", "direction", "outcome", "limitation",
    ],
    "LK-KURAL": [
        "kural", "tamil", "thirukkural",
        "universal principle", "compressed title", "moral",
    ],
    "LK-EDITOR": [
        "article", "editorial", "heading", "disclaimer",
        "plain language", "word count", "publication status", "story",
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def flatten_findings(report: dict[str, Any]) -> list[str]:
    findings: list[str] = []

    for key in ["blocking_errors", "review_findings"]:
        for item in report.get(key, []):
            if isinstance(item, str):
                findings.append(item)

    for artifact in report.get("artifact_findings", []):
        if not isinstance(artifact, dict):
            continue

        name = str(artifact.get("artifact") or "artifact")
        status = str(artifact.get("status") or "")
        for item in artifact.get("findings", []):
            if isinstance(item, str):
                findings.append(f"{name} [{status}]: {item}")

    return findings


def owner_for_finding(finding: str) -> str:
    lowered = finding.lower()
    scores = {
        stage: sum(
            1 for keyword in keywords
            if keyword in lowered
        )
        for stage, keywords in KEYWORDS.items()
    }

    best_stage = max(scores, key=scores.get)
    return best_stage if scores[best_stage] else "LK-EDITOR"


def build_remediation_plan(
    case_id: str,
    qa_report: dict[str, Any],
) -> dict[str, Any]:
    findings = flatten_findings(qa_report)
    work_items: list[dict[str, Any]] = []

    for index, finding in enumerate(findings, start=1):
        work_items.append(
            {
                "work_item_id": f"REM-{index:03d}",
                "owner": owner_for_finding(finding),
                "finding": finding,
                "status": "PENDING",
            }
        )

    if not work_items:
        work_items.append(
            {
                "work_item_id": "REM-001",
                "owner": "LK-EDITOR",
                "finding": (
                    "QA returned REVIEW_REQUIRED without a specific "
                    "machine-readable finding. Re-audit editorial fidelity."
                ),
                "status": "PENDING",
            }
        )

    owners = sorted(
        {item["owner"] for item in work_items},
        key=STAGE_ORDER.index,
    )

    return {
        "schema_version": "1.0",
        "agent_id": "LK-REMEDIATION",
        "case_id": case_id,
        "status": "PLANNED",
        "created_at_utc": utc_now(),
        "qa_verdict": qa_report.get("verdict"),
        "qa_confidence": qa_report.get("confidence"),
        "earliest_owner": owners[0],
        "owners": owners,
        "work_items": work_items,
        "publication_ready": False,
    }


def command(
    root: Path,
    executable: str,
    case_id: str,
    case_root: Path,
    provider: str | None = None,
    allow_live: bool = False,
) -> list[str]:
    result = [
        str(root / "bin" / executable),
        "--case-id",
        case_id,
        "--case-root",
        str(case_root),
    ]

    if provider:
        result.extend(["--provider", provider])

    if allow_live:
        result.append("--allow-live")

    return result


def run_command(root: Path, args: list[str]) -> None:
    subprocess.run(args, cwd=root, check=True)


def stages_from(owner: str) -> list[str]:
    return STAGE_ORDER[STAGE_ORDER.index(owner):]


def execute_remediation(
    root: Path,
    case_id: str,
    case_root: Path,
    provider: str,
    allow_live: bool,
    max_iterations: int,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()
    qa_path = case_root / "evidence/qa-model-review-report.json"
    iterations: list[dict[str, Any]] = []

    for iteration in range(1, max_iterations + 1):
        qa_report = read_json(qa_path)

        if qa_report.get("verdict") == "PASS":
            break

        plan = build_remediation_plan(case_id, qa_report)
        plan["iteration"] = iteration

        write_json(
            case_root / f"evidence/remediation-plan-{iteration:03d}.json",
            plan,
        )

        execution: list[dict[str, Any]] = []

        for stage in stages_from(plan["earliest_owner"]):
            started = utc_now()

            if stage == "LK-EXTRACT":
                steps = [
                    command(root, "aidpl-review-extract", case_id, case_root, provider, allow_live),
                    command(root, "aidpl-review-run", case_id, case_root),
                ]
            elif stage == "LK-LAW":
                steps = [
                    command(root, "aidpl-review-law", case_id, case_root, provider, allow_live),
                    command(root, "aidpl-review-after-law", case_id, case_root),
                ]
            elif stage == "LK-REASON":
                steps = [
                    command(root, "aidpl-review-reason", case_id, case_root, provider, allow_live),
                    command(root, "aidpl-review-after-reason", case_id, case_root),
                ]
            elif stage == "LK-KURAL":
                steps = [
                    command(root, "aidpl-review-kural", case_id, case_root, provider, allow_live),
                    command(root, "aidpl-review-after-kural", case_id, case_root),
                ]
            elif stage == "LK-EDITOR":
                steps = [
                    command(root, "aidpl-review-editor", case_id, case_root, provider, allow_live),
                    command(root, "aidpl-review-after-editor", case_id, case_root),
                ]
            else:
                steps = [
                    command(root, "aidpl-review-qa", case_id, case_root, provider, allow_live),
                ]

            try:
                for step in steps:
                    run_command(root, step)
                status = "COMPLETE"
                error = None
            except subprocess.CalledProcessError as exc:
                status = "FAILED"
                error = (
                    f"Command failed with exit status "
                    f"{exc.returncode}: {' '.join(exc.cmd)}"
                )

            execution.append(
                {
                    "stage": stage,
                    "status": status,
                    "started_at_utc": started,
                    "completed_at_utc": utc_now(),
                    "error": error,
                }
            )

            if status == "FAILED":
                break

        latest_qa = read_json(qa_path)

        iteration_report = {
            "iteration": iteration,
            "plan": plan,
            "execution": execution,
            "qa_verdict_after_iteration": latest_qa.get("verdict"),
            "qa_confidence_after_iteration": latest_qa.get("confidence"),
            "completed_at_utc": utc_now(),
        }
        iterations.append(iteration_report)

        write_json(
            case_root / f"evidence/remediation-iteration-{iteration:03d}.json",
            iteration_report,
        )

        if any(step["status"] == "FAILED" for step in execution):
            break

        if latest_qa.get("verdict") == "PASS":
            break

    final_qa = read_json(qa_path)

    report = {
        "schema_version": "1.0",
        "runtime": "AIDPL Autonomous Remediation Runtime",
        "runtime_version": "0.1.0",
        "case_id": case_id,
        "status": (
            "PASS"
            if final_qa.get("verdict") == "PASS"
            else "STOPPED_WITH_REVIEW_REQUIRED"
        ),
        "completed_at_utc": utc_now(),
        "iterations": iterations,
        "final_qa_verdict": final_qa.get("verdict"),
        "final_qa_confidence": final_qa.get("confidence"),
        "founder_gate": (
            "OPEN"
            if final_qa.get("verdict") == "PASS"
            else "BLOCKED"
        ),
        "publication_ready": False,
        "next_action": (
            "FOUNDER_REVIEW"
            if final_qa.get("verdict") == "PASS"
            else "HUMAN_EXCEPTION_REVIEW"
        ),
    }

    write_json(
        case_root / "evidence/remediation-runtime-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-remediate",
        description="Plan and execute autonomous Legal Kural remediation.",
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai", "deepseek", "qwen"],
    )
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--max-iterations", type=int, default=1)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(__file__).resolve().parents[2]

    if args.provider != "mock" and not args.allow_live:
        print("ERROR: Live remediation requires --allow-live.", file=sys.stderr)
        return 1

    if args.max_iterations < 1 or args.max_iterations > 3:
        print(
            "ERROR: --max-iterations must be between 1 and 3.",
            file=sys.stderr,
        )
        return 1

    try:
        report = execute_remediation(
            root=root,
            case_id=args.case_id,
            case_root=args.case_root,
            provider=args.provider,
            allow_live=args.allow_live,
            max_iterations=args.max_iterations,
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
    print("LEGAL KURAL AUTONOMOUS REMEDIATION")
    print("=" * 76)
    print(f"Case        : {args.case_id}")
    print(f"Iterations  : {len(report['iterations'])}")
    print(f"Final QA    : {report['final_qa_verdict']}")
    print(f"Confidence  : {report['final_qa_confidence']}")
    print(f"Founder Gate: {report['founder_gate']}")
    print(f"Next Action : {report['next_action']}")
    print("=" * 76)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
