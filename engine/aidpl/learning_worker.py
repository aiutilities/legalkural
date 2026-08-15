from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .orchestrator import complete_agent, load_plan, save_plan, start_agent


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def render_review(
    case_id: str,
    plan: dict[str, Any],
    qa: dict[str, Any],
    editorial: dict[str, Any],
) -> str:
    completed = [
        agent["agent_id"]
        for agent in plan["agents"]
        if agent["status"] == "COMPLETE"
    ]

    return f"""# Thinking Review — {case_id}

**Status:** Complete
**QA Verdict:** {qa.get('verdict', 'UNKNOWN')}
**Publication Ready:** {qa.get('publication_ready', False)}

## What Worked

- The full AIDPL pipeline executed from intake through QA.
- Agent dependencies were enforced by the orchestrator.
- Each worker produced machine-readable evidence.
- The article draft was generated from structured artifacts.
- Publication remained blocked when QA required review.

## What Needs Improvement

- Preserve only lessons supported by the completed case evidence.
- Separate case-specific corrections from reusable pipeline improvements.
- Regulation and precedent detection should continue to be measured for recall.
- Learning must never modify certified publication artifacts.
- Publication state must be taken from the current QA evidence, not assumed.

## Reusable Pattern

```text
Judgment
  ↓
Intake
  ↓
Extraction
  ↓
Law
  ↓
Reasoning
  ↓
Kural
  ↓
Editorial
  ↓
QA
  ↓
Learning
```

## Engineering Metrics

- Completed agents: {len(completed)}
- Article word count: {editorial.get('word_count', 0)}
- QA checks: {len(qa.get('checks', []))}
- QA blockers: {len(qa.get('blocking_errors', []))}
- QA review items: {len(qa.get('review_reasons', []))}

## AIDPL Lessons

1. Agent completion and QA approval must remain separate.
2. Publication requires both QA PASS and Founder authorization.
3. Deterministic workers are useful for structure, but not sufficient for final legal interpretation.
4. Every worker must leave evidence for the next agent.
5. LearningOS may run even when publication is blocked.

## Next Evolution

Connect model-assisted legal review to:

- LK-EXTRACT
- LK-LAW
- LK-REASON
- LK-KURAL
- LK-EDITOR
- LK-QA

## Post-Case Governance

- If QA is not publication-ready, learning output must not represent the case as certified.
- If QA is publication-ready, treat learning as post-certification analysis.
- Learning must not alter the certified source, legal artifacts, Kural, article, or QA evidence.
"""


def run_learning(
    case_id: str,
    case_root: Path,
    plan_path: Path,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()
    plan = read_json(plan_path)
    qa = read_json(case_root / "evidence/validation-report.json")
    editorial = read_json(case_root / "evidence/editorial-report.json")

    review = render_review(case_id, plan, qa, editorial)

    output_path = (
        case_root
        / "output/11-learning/thinking-review.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(review.rstrip() + "\n", encoding="utf-8")

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-LEARN",
        "case_id": case_id,
        "status": "COMPLETE",
        "completed_at_utc": utc_now(),
        "output": str(output_path),
        "qa_verdict": qa.get("verdict"),
        "publication_ready": qa.get("publication_ready", False),
        "next_action": (
            "POST_CERTIFICATION_LEARNING_REVIEW"
            if qa.get("publication_ready") is True
            else "MODEL_ASSISTED_REVIEW"
            if qa.get("verdict") == "REVIEW_REQUIRED"
            else "REMEDIATION_REQUIRED"
        ),
    }

    report_path = case_root / "evidence/learning-report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-learn",
        description="Run the Legal Kural LearningOS Agent.",
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        plan = load_plan(args.plan)
        start_agent(plan, "LK-LEARN")
        save_plan(args.plan, plan)

        report = run_learning(
            case_id=args.case_id,
            case_root=args.case_root,
            plan_path=args.plan,
        )

        plan = load_plan(args.plan)
        complete_agent(
            plan,
            "LK-LEARN",
            reviewer="AI-CEO",
            note="Thinking review and LearningOS report created.",
        )
        save_plan(args.plan, plan)

        print()
        print("=" * 72)
        print("LEGAL KURAL LEARNINGOS AGENT")
        print("=" * 72)
        print(f"Case        : {args.case_id}")
        print(f"QA Verdict  : {report['qa_verdict']}")
        print(f"Publish     : {report['publication_ready']}")
        print(f"Next Action : {report['next_action']}")
        print("Status      : COMPLETE")
        print("=" * 72)
        return 0

    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
