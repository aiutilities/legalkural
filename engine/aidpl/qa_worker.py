from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .orchestrator import complete_agent, load_plan, save_plan, start_agent


REQUIRED_ARTIFACTS = [
    "manifest.json",
    "evidence/source-integrity.json",
    "evidence/intake-report.json",
    "evidence/extraction-report.json",
    "evidence/law-analysis-report.json",
    "evidence/reasoning-analysis-report.json",
    "evidence/kural-generation-report.json",
    "evidence/editorial-report.json",
    "output/01-metadata/metadata.json",
    "output/02-timeline/timeline.json",
    "output/03-facts/facts.json",
    "output/04-issues/issues.json",
    "output/05-evidence/evidence.json",
    "output/06-law/law.json",
    "output/07-reasoning/reasoning.json",
    "output/08-decision/decision.json",
    "output/09-kural/kural-brief.json",
    "output/09-kural/kural.md",
    "output/10-article/article.md",
]

REVIEW_MARKERS = {
    "REQUIRES_MODEL_REVIEW",
    "MODEL_REVIEW_REQUIRED",
    "EDITORIAL_DRAFT_REQUIRES_REVIEW",
    "COMPLETE_WITH_MODEL_REVIEW_REQUIRED",
    "COMPLETE_WITH_EDITORIAL_REVIEW_REQUIRED",
    "COMPLETE_WITH_QA_REQUIRED",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_status_markers(value: Any) -> set[str]:
    markers: set[str] = set()

    if isinstance(value, dict):
        for key, item in value.items():
            if key == "status" and isinstance(item, str):
                markers.add(item)
            markers.update(collect_status_markers(item))
    elif isinstance(value, list):
        for item in value:
            markers.update(collect_status_markers(item))

    return markers


def run_qa(case_id: str, case_root: Path) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()

    checks: list[dict[str, Any]] = []
    blocking_errors: list[str] = []
    review_reasons: list[str] = []

    for relative in REQUIRED_ARTIFACTS:
        path = case_root / relative

        if not path.exists():
            checks.append({
                "path": relative,
                "status": "FAIL",
                "message": "Required artifact is missing.",
            })
            blocking_errors.append(f"Missing artifact: {relative}")
            continue

        if path.stat().st_size == 0:
            checks.append({
                "path": relative,
                "status": "FAIL",
                "message": "Artifact is empty.",
            })
            blocking_errors.append(f"Empty artifact: {relative}")
            continue

        if path.suffix == ".json":
            try:
                payload = read_json(path)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                checks.append({
                    "path": relative,
                    "status": "FAIL",
                    "message": f"Invalid JSON: {exc}",
                })
                blocking_errors.append(f"Invalid JSON: {relative}")
                continue

            checks.append({
                "path": relative,
                "status": "PASS",
                "payload_status": payload.get("status"),
            })

            superseded_stage_reports = {
                "evidence/extraction-report.json",
                "evidence/law-analysis-report.json",
                "evidence/reasoning-analysis-report.json",
                "evidence/kural-generation-report.json",
                "evidence/editorial-report.json",
            }

            for marker in sorted(
                collect_status_markers(payload) & REVIEW_MARKERS
            ):
                if relative not in superseded_stage_reports:
                    review_reasons.append(
                        f"{relative}: {marker}"
                    )
        else:
            checks.append({
                "path": relative,
                "status": "PASS",
                "message": "Non-empty text artifact.",
            })

    article_path = case_root / "output/10-article/article.md"
    kural_path = case_root / "output/09-kural/kural.md"

    article = (
        article_path.read_text(encoding="utf-8")
        if article_path.exists()
        else ""
    )
    kural = (
        kural_path.read_text(encoding="utf-8")
        if kural_path.exists()
        else ""
    )

    article_requirements = [
        ("not personalised legal advice",),
        (
            "Founder authorises publication",
            "Founder approval",
        ),
        ("Publication status",),
    ]

    for alternatives in article_requirements:
        if not any(
            phrase.lower() in article.lower()
            for phrase in alternatives
        ):
            blocking_errors.append(
                "Article missing required phrase: "
                + " OR ".join(alternatives)
            )


    if re.search(
        r"^\s*##?\s+Kural-Inspired Tamil\s*$",
        kural,
        re.MULTILINE,
    ):
        if "pending" not in kural.lower() and "deferred" not in kural.lower():
            review_reasons.append(
                "Tamil editorial content requires independent review."
            )

    if blocking_errors:
        verdict = "FAIL"
    elif review_reasons:
        verdict = "REVIEW_REQUIRED"
    else:
        verdict = "PASS"

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-QA",
        "case_id": case_id,
        "status": "COMPLETE",
        "completed_at_utc": utc_now(),
        "verdict": verdict,
        "checks": checks,
        "blocking_errors": sorted(set(blocking_errors)),
        "review_reasons": sorted(set(review_reasons)),
        "publication_ready": verdict == "PASS",
        "next_agent": "LK-LEARN",
    }

    report_path = case_root / "evidence/validation-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-qa",
        description="Run Legal Fidelity and QA Agent.",
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    plan = None

    try:
        if args.plan:
            plan = load_plan(args.plan)
            start_agent(plan, "LK-QA")
            save_plan(args.plan, plan)

        report = run_qa(args.case_id, args.case_root)

        if args.plan and plan is not None:
            plan = load_plan(args.plan)
            complete_agent(
                plan,
                "LK-QA",
                reviewer="AI-CEO",
                note=f"QA completed with verdict {report['verdict']}.",
                verdict=report["verdict"],
            )
            save_plan(args.plan, plan)

        print()
        print("=" * 72)
        print("LEGAL KURAL FIDELITY AND QA AGENT")
        print("=" * 72)
        print(f"Case        : {args.case_id}")
        print(f"Verdict     : {report['verdict']}")
        print(f"Checks      : {len(report['checks'])}")
        print(f"Blockers    : {len(report['blocking_errors'])}")
        print(f"Reviews     : {len(report['review_reasons'])}")
        print(f"Publish     : {report['publication_ready']}")
        print("Next Agent  : LK-LEARN")
        print("=" * 72)
        return 0 if report["verdict"] != "FAIL" else 1

    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
