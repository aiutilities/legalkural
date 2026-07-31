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


def text_of(item: Any) -> str:
    if isinstance(item, str):
        return " ".join(item.split())
    if isinstance(item, dict):
        for key in ("text", "question", "fact", "finding", "event"):
            value = item.get(key)
            if value:
                return " ".join(str(value).split())
    return ""


def first(items: list[Any], fallback: str) -> str:
    for item in items:
        value = text_of(item)
        if value:
            return value
    return fallback


def bullet_list(items: list[Any], limit: int = 8) -> str:
    rows = []
    for item in items[:limit]:
        value = text_of(item)
        if value:
            rows.append(f"- {value}")
    return "\n".join(rows) if rows else "- No verified item available."


def build_article(
    case_id: str,
    metadata: dict[str, Any],
    timeline: dict[str, Any],
    facts: dict[str, Any],
    issues: dict[str, Any],
    evidence: dict[str, Any],
    law: dict[str, Any],
    reasoning: dict[str, Any],
    decision: dict[str, Any],
    kural: dict[str, Any],
) -> str:
    title = kural.get("compressed_title") or "Legal Kural Case Analysis"
    court = metadata.get("court") or "Court not yet verified"
    judge = metadata.get("judge") or "Judge not yet verified"
    outcome = decision.get("outcome") or "Outcome requires review"

    issue_text = first(
        issues.get("issues", []),
        "The legal issue requires model-assisted review.",
    )
    holding = kural.get("legal_holding") or first(
        reasoning.get("ratio_candidates", []),
        "The legal holding requires model-assisted review.",
    )
    principle = kural.get("universal_principle") or (
        "Verified facts, applicable law and fair procedure must guide judgment."
    )

    return f"""# {title}

**Reference Case:** {case_id}

> **Publication status:** Draft generated from deterministic artifacts. Legal
> fidelity, editorial quality and source citations require independent review.

## Case Snapshot

| Item | Detail |
|---|---|
| Court | {court} |
| Judge | {judge} |
| Outcome | {outcome} |
| Case ID | {case_id} |

## Kural-Inspired Insight

> **{kural.get('kural_inspired_english', 'Editorial insight pending.')}**

This is original Legal Kural editorial writing. It is not an authentic
Thirukkural verse.

## What Is the Case About?

{issue_text}

## What Happened?

{bullet_list(facts.get('material_facts', []), 10)}

## Important Timeline

{bullet_list(timeline.get('events', []), 10)}

## Evidence Considered

### Documentary Evidence

{bullet_list(evidence.get('documentary_evidence', []), 8)}

### Evidence Identified as Missing

{bullet_list(evidence.get('missing_evidence', []), 8)}

## Applicable Law

### Constitutional Provisions

{bullet_list(law.get('constitutional_provisions', []), 8)}

### Statutes and Regulations

{bullet_list(
    law.get('statutes', []) + law.get('regulations', []),
    12,
)}

### Precedents

{bullet_list(law.get('precedents', []), 8)}

## How the Judge Reasoned

{bullet_list(reasoning.get('reasoning_steps', []), 12)}

## The Holding

{holding}

## The Decision

{bullet_list(decision.get('operative_directions', []), 10)}

## Limits of the Ruling

{bullet_list(decision.get('limitations', []), 8)}

## For the Citizen

The Court's decision should be understood through the verified facts, the
actual legal provisions and the procedure followed. Labels alone do not
replace evidence.

## For the Law Student

Study how the judgment moves from facts to issues, from legal authorities to
reasoning, and from reasoning to operative relief. The distinction between the
holding and broader observations must be preserved.

## For the Lawyer

Verify every proposition against the source judgment before relying on this
draft. Review jurisdiction, maintainability, statutory interpretation,
precedent treatment, relief and factual limitations separately.

## Universal Principle

{principle}

## Editorial Disclaimer

This draft is an educational explanation generated from structured artifacts.

It is not personalised legal advice.

It must not be published until the Legal Fidelity and QA Agent records a pass
and the Founder authorises publication.
"""


def run_editor(case_id: str, case_root: Path) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()
    output = case_root / "output"

    metadata = read_json(output / "01-metadata/metadata.json")
    timeline = read_json(output / "02-timeline/timeline.json")
    facts = read_json(output / "03-facts/facts.json")
    issues = read_json(output / "04-issues/issues.json")
    evidence = read_json(output / "05-evidence/evidence.json")
    law = read_json(output / "06-law/law.json")
    reasoning = read_json(output / "07-reasoning/reasoning.json")
    decision = read_json(output / "08-decision/decision.json")
    kural = read_json(output / "09-kural/kural-brief.json")

    article = build_article(
        case_id,
        metadata,
        timeline,
        facts,
        issues,
        evidence,
        law,
        reasoning,
        decision,
        kural,
    )

    article_path = output / "10-article/article.md"
    article_path.parent.mkdir(parents=True, exist_ok=True)
    article_path.write_text(article.rstrip() + "\n", encoding="utf-8")

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-EDITOR",
        "case_id": case_id,
        "status": "COMPLETE_WITH_QA_REQUIRED",
        "completed_at_utc": utc_now(),
        "output": str(article_path),
        "word_count": len(article.split()),
        "qa_required": True,
        "next_agent": "LK-QA",
    }

    report_path = case_root / "evidence/editorial-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-editor",
        description="Generate the Legal Kural article draft.",
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
            start_agent(plan, "LK-EDITOR")
            save_plan(args.plan, plan)

        report = run_editor(args.case_id, args.case_root)

        if args.plan and plan is not None:
            plan = load_plan(args.plan)
            complete_agent(
                plan,
                "LK-EDITOR",
                reviewer="AI-CEO",
                note="Deterministic article draft created; QA remains mandatory.",
            )
            save_plan(args.plan, plan)

        print()
        print("=" * 72)
        print("LEGAL KURAL EDITORIAL AGENT")
        print("=" * 72)
        print(f"Case       : {args.case_id}")
        print(f"Words      : {report['word_count']}")
        print("Article    : CREATED")
        print("QA         : REQUIRED")
        print("Next Agent : LK-QA")
        print("=" * 72)
        return 0
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
