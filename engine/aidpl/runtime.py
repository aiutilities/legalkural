from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKERS = [
    ("LK-INTAKE", "aidpl-intake"),
    ("LK-EXTRACT", "aidpl-extract"),
    ("LK-LAW", "aidpl-law"),
    ("LK-REASON", "aidpl-reason"),
    ("LK-KURAL", "aidpl-kural"),
    ("LK-EDITOR", "aidpl-editor"),
    ("LK-QA", "aidpl-qa"),
    ("LK-LEARN", "aidpl-learn"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_command(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def build_worker_command(
    root: Path,
    worker: str,
    case_id: str,
    case_root: Path,
    plan_path: Path,
    source_pdf: Path,
    overwrite: bool,
) -> list[str]:
    executable = root / "bin" / worker

    if worker == "aidpl-intake":
        command = [
            str(executable),
            str(source_pdf),
            "--case-id",
            case_id,
            "--case-root",
            str(case_root),
            "--plan",
            str(plan_path),
        ]
        if overwrite:
            command.append("--overwrite")
        return command

    return [
        str(executable),
        "--case-id",
        case_id,
        "--case-root",
        str(case_root),
        "--plan",
        str(plan_path),
    ]


def run_pipeline(
    root: Path,
    source_pdf: Path,
    case_id: str,
    output_root: Path,
    overwrite: bool,
) -> dict[str, Any]:
    source_pdf = source_pdf.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    case_root = output_root / case_id
    plan_path = case_root / "aidpl-plan.json"

    if case_root.exists():
        if not overwrite:
            raise FileExistsError(
                f"Case already exists: {case_root}. "
                "Use --overwrite to replace it."
            )
        shutil.rmtree(case_root)

    run_command(
        [
            str(root / "bin/legalkural"),
            str(source_pdf),
            "--case-id",
            case_id,
            "--output-root",
            str(output_root),
        ],
        root,
    )

    run_command(
        [
            str(root / "bin/aidpl-orchestrator"),
            "init",
            "--case-id",
            case_id,
            "--case-root",
            str(case_root),
            "--plan",
            str(plan_path),
        ],
        root,
    )

    execution: list[dict[str, Any]] = []
    started_at = utc_now()

    for agent_id, worker in WORKERS:
        command = build_worker_command(
            root=root,
            worker=worker,
            case_id=case_id,
            case_root=case_root,
            plan_path=plan_path,
            source_pdf=source_pdf,
            overwrite=overwrite,
        )

        step_started = utc_now()

        try:
            run_command(command, root)
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
                "started_at_utc": step_started,
                "completed_at_utc": utc_now(),
                "error": error,
            }
        )

        if status == "FAILED":
            break

    plan = read_json(plan_path)
    qa_status = plan["publication"]["qa_status"]
    founder_status = plan["publication"]["founder_authorization"]
    publish_ready = plan["publication"]["ready"]

    runtime_status = (
        "COMPLETE"
        if all(step["status"] == "COMPLETE" for step in execution)
        else "FAILED"
    )

    report = {
        "schema_version": "1.0",
        "runtime": "AIDPL Runtime",
        "runtime_version": "0.1.0",
        "case_id": case_id,
        "case_root": str(case_root),
        "status": runtime_status,
        "started_at_utc": started_at,
        "completed_at_utc": utc_now(),
        "execution": execution,
        "agent_plan_status": plan["status"],
        "publication": {
            "qa_status": qa_status,
            "founder_authorization": founder_status,
            "ready": publish_ready,
        },
        "next_action": (
            "MODEL_ASSISTED_REVIEW"
            if qa_status == "REVIEW_REQUIRED"
            else (
                "FOUNDER_AUTHORIZATION"
                if qa_status == "PASS" and founder_status != "AUTHORIZED"
                else (
                    "PUBLICATION_READY"
                    if publish_ready
                    else "ATTENTION_REQUIRED"
                )
            )
        ),
    }

    write_json(case_root / "evidence/runtime-report.json", report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-run",
        description=(
            "Run the complete Legal Kural AIDPL deterministic pipeline "
            "from one judgment PDF."
        ),
    )
    parser.add_argument("source_pdf", type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("generated"),
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(__file__).resolve().parents[2]

    try:
        report = run_pipeline(
            root=root,
            source_pdf=args.source_pdf,
            case_id=args.case_id,
            output_root=args.output_root,
            overwrite=args.overwrite,
        )
    except (
        FileExistsError,
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print()
    print("=" * 76)
    print("LEGAL KURAL AIDPL RUNTIME")
    print("=" * 76)
    print(f"Case        : {report['case_id']}")
    print(f"Status      : {report['status']}")
    print(f"Agents      : {len(report['execution'])}")
    print(f"QA          : {report['publication']['qa_status']}")
    print(f"Founder     : {report['publication']['founder_authorization']}")
    print(f"Publish     : {report['publication']['ready']}")
    print(f"Next Action : {report['next_action']}")
    print("=" * 76)

    return 0 if report["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
