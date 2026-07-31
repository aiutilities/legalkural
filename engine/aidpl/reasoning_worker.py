from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import validate

from .extraction_worker import load_pages
from .orchestrator import (
    complete_agent,
    load_plan,
    save_plan,
    start_agent,
)


REASONING_MARKERS = [
    "this court is of the considered view",
    "this court holds",
    "this court finds",
    "in view of the above",
    "in the light of the above",
    "therefore",
    "accordingly",
    "it is clear that",
]

ACCEPTED_MARKERS = [
    "this court accepts",
    "the contention of the petitioner",
    "the submission of the petitioner",
    "we agree",
    "this court is inclined to accept",
]

REJECTED_MARKERS = [
    "cannot be accepted",
    "is rejected",
    "this court is unable to accept",
    "the contention of the respondent",
    "the submission of the respondent",
]

LIMITATION_MARKERS = [
    "applicable only",
    "cannot be followed in a blindfolded manner",
    "subject to verification",
    "unless and otherwise",
    "on the facts of the present case",
]

ORDER_MARKERS = [
    "following order",
    "impugned notices are liable to be quashed",
    "accordingly, the same are quashed",
    "writ petitions are allowed",
    "writ petitions are dismissed",
    "no cost",
    "no costs",
    "miscellaneous petitions are closed",
]

OUTCOME_PATTERNS = [
    (re.compile(r"\bwrit petitions? (?:are|is) allowed\b", re.I), "Allowed"),
    (re.compile(r"\bwrit petitions? (?:are|is) dismissed\b", re.I), "Dismissed"),
    (re.compile(r"\bpartly allowed\b", re.I), "Partly Allowed"),
    (re.compile(r"\bdisposed of\b", re.I), "Disposed"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def compact(value: str) -> str:
    return " ".join(value.split()).strip()


def extract_context(
    text: str,
    start: int,
    end: int,
    width: int = 260,
) -> str:
    return compact(
        text[max(0, start - width):min(len(text), end + width)]
    )


def collect_marker_candidates(
    pages: list[dict[str, Any]],
    markers: list[str],
    limit: int = 50,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()

    for page in pages:
        text = page["text"]
        lowered = text.lower()

        for marker in markers:
            start = 0

            while True:
                index = lowered.find(marker, start)

                if index < 0:
                    break

                candidate_text = extract_context(
                    text,
                    index,
                    index + len(marker),
                )
                key = (candidate_text, page["page"])

                if key not in seen:
                    seen.add(key)
                    candidates.append(
                        {
                            "text": candidate_text,
                            "source_pages": [page["page"]],
                            "status": "CANDIDATE",
                        }
                    )

                start = index + len(marker)

                if len(candidates) >= limit:
                    return candidates

    return candidates


def normalize_issues(
    issues_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    normalized = []

    for index, item in enumerate(issues_artifact.get("issues", []), start=1):
        question = item.get("question") or item.get("title") or str(item)

        normalized.append(
            {
                "issue_id": f"I{index:03d}",
                "question": compact(question),
                "source_pages": item.get("source_pages", []),
                "status": "CANDIDATE",
            }
        )

    return normalized


def build_reasoning(
    case_id: str,
    pages: list[dict[str, Any]],
    facts: dict[str, Any],
    issues: dict[str, Any],
    law: dict[str, Any],
) -> dict[str, Any]:
    reasoning_steps = collect_marker_candidates(
        pages,
        REASONING_MARKERS,
        limit=60,
    )
    accepted = collect_marker_candidates(
        pages,
        ACCEPTED_MARKERS,
        limit=20,
    )
    rejected = collect_marker_candidates(
        pages,
        REJECTED_MARKERS,
        limit=20,
    )
    limitations = collect_marker_candidates(
        pages,
        LIMITATION_MARKERS,
        limit=20,
    )

    ratio_candidates = list(law.get("ratio_candidates", []))

    if not ratio_candidates:
        ratio_candidates = reasoning_steps[:20]

    traceability = []

    for category, items in [
        ("issues", normalize_issues(issues)),
        ("reasoning_steps", reasoning_steps),
        ("accepted_arguments", accepted),
        ("rejected_arguments", rejected),
        ("ratio_candidates", ratio_candidates),
        ("limitations", limitations),
    ]:
        for item in items:
            traceability.append(
                {
                    "category": category,
                    "source_pages": item.get("source_pages", []),
                }
            )

    return {
        "schema_version": "1.0",
        "reference_case_id": case_id,
        "status": "REQUIRES_MODEL_REVIEW",
        "issues": normalize_issues(issues),
        "reasoning_steps": reasoning_steps,
        "accepted_arguments": accepted,
        "rejected_arguments": rejected,
        "ratio_candidates": ratio_candidates[:30],
        "limitations": limitations,
        "source_traceability": traceability,
        "inputs_summary": {
            "material_fact_candidates": len(
                facts.get("material_facts", [])
            ),
            "issue_candidates": len(
                issues.get("issues", [])
            ),
            "legal_authorities": (
                len(law.get("constitutional_provisions", []))
                + len(law.get("statutes", []))
                + len(law.get("regulations", []))
                + len(law.get("notifications", []))
                + len(law.get("precedents", []))
            ),
        },
        "quality_notes": [
            "Reasoning steps were detected from judicial transition markers.",
            "Accepted and rejected argument classification is provisional.",
            "Final ratio decidendi requires model-assisted legal review.",
            "No editorial interpretation has been added."
        ]
    }


def detect_outcome(pages: list[dict[str, Any]]) -> str | None:
    for page in reversed(pages):
        for pattern, outcome in OUTCOME_PATTERNS:
            if pattern.search(page["text"]):
                return outcome
    return None


def build_decision(
    case_id: str,
    pages: list[dict[str, Any]],
    reasoning: dict[str, Any],
) -> dict[str, Any]:
    operative = collect_marker_candidates(
        pages,
        ORDER_MARKERS,
        limit=40,
    )
    limitations = reasoning.get("limitations", [])

    relief_granted = []
    relief_denied = []
    costs = None

    for item in operative:
        lowered = item["text"].lower()

        if (
            "quashed" in lowered
            or "allowed" in lowered
            or "directed" in lowered
        ):
            relief_granted.append(item)

        if (
            "dismissed" in lowered
            or "rejected" in lowered
            or "denied" in lowered
        ):
            relief_denied.append(item)

        if "no cost" in lowered or "no costs" in lowered:
            costs = "No order as to costs."

    outcome = detect_outcome(pages)

    traceability = []

    for category, items in [
        ("operative_directions", operative),
        ("relief_granted", relief_granted),
        ("relief_denied", relief_denied),
        ("limitations", limitations),
    ]:
        for item in items:
            traceability.append(
                {
                    "category": category,
                    "source_pages": item.get("source_pages", []),
                }
            )

    return {
        "schema_version": "1.0",
        "reference_case_id": case_id,
        "status": "REQUIRES_MODEL_REVIEW",
        "outcome": outcome,
        "operative_directions": operative,
        "relief_granted": relief_granted,
        "relief_denied": relief_denied,
        "costs": costs,
        "limitations": limitations,
        "source_traceability": traceability,
        "quality_notes": [
            "Outcome and operative directions were detected deterministically.",
            "Relief categorisation requires legal review.",
            "The worker does not infer remedies absent from the judgment."
        ]
    }


def validate_artifact(
    artifact: dict[str, Any],
    schema_path: Path,
) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=artifact, schema=schema)


def run_reasoning_analysis(
    case_id: str,
    case_root: Path,
    schema_root: Path,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()

    pages = load_pages(case_root / "working/source-text.txt")
    facts = read_json(case_root / "output/03-facts/facts.json")
    issues = read_json(case_root / "output/04-issues/issues.json")
    law = read_json(case_root / "output/06-law/law.json")

    reasoning = build_reasoning(
        case_id=case_id,
        pages=pages,
        facts=facts,
        issues=issues,
        law=law,
    )
    decision = build_decision(
        case_id=case_id,
        pages=pages,
        reasoning=reasoning,
    )

    validate_artifact(
        reasoning,
        schema_root / "reasoning.schema.json",
    )
    validate_artifact(
        decision,
        schema_root / "decision.schema.json",
    )

    reasoning_path = case_root / "output/07-reasoning/reasoning.json"
    decision_path = case_root / "output/08-decision/decision.json"

    write_json(reasoning_path, reasoning)
    write_json(decision_path, decision)

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-REASON",
        "case_id": case_id,
        "status": "COMPLETE_WITH_MODEL_REVIEW_REQUIRED",
        "completed_at_utc": utc_now(),
        "outputs": [
            str(reasoning_path),
            str(decision_path),
        ],
        "schema_validation": {
            "reasoning.schema.json": "PASS",
            "decision.schema.json": "PASS",
        },
        "counts": {
            "issues": len(reasoning["issues"]),
            "reasoning_steps": len(reasoning["reasoning_steps"]),
            "accepted_arguments": len(reasoning["accepted_arguments"]),
            "rejected_arguments": len(reasoning["rejected_arguments"]),
            "ratio_candidates": len(reasoning["ratio_candidates"]),
            "operative_directions": len(
                decision["operative_directions"]
            ),
            "limitations": len(decision["limitations"]),
        },
        "outcome": decision["outcome"],
        "model_review_required": True,
        "next_agent": "LK-KURAL",
    }

    write_json(
        case_root / "evidence/reasoning-analysis-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-reason",
        description="Run deterministic Judicial Reasoning Agent foundation.",
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    plan = None

    try:
        if args.plan:
            plan = load_plan(args.plan)
            start_agent(plan, "LK-REASON")
            save_plan(args.plan, plan)

        root = Path(__file__).resolve().parents[2]
        report = run_reasoning_analysis(
            case_id=args.case_id,
            case_root=args.case_root,
            schema_root=root / "engine/schemas",
        )

        if args.plan and plan is not None:
            plan = load_plan(args.plan)
            complete_agent(
                plan,
                "LK-REASON",
                reviewer="AI-CEO",
                note=(
                    "Deterministic reasoning and decision extraction "
                    "passed schema validation; model review remains required."
                ),
            )
            save_plan(args.plan, plan)

        print()
        print("=" * 72)
        print("LEGAL KURAL JUDICIAL REASONING AGENT")
        print("=" * 72)
        print(f"Case         : {args.case_id}")
        print(f"Issues       : {report['counts']['issues']}")
        print(
            "Reasoning    : "
            f"{report['counts']['reasoning_steps']} candidates"
        )
        print(
            "Ratio        : "
            f"{report['counts']['ratio_candidates']} candidates"
        )
        print(
            "Directions   : "
            f"{report['counts']['operative_directions']}"
        )
        print(f"Outcome      : {report['outcome']}")
        print("Schemas      : PASS")
        print("Model Review : REQUIRED")
        print("Next Agent   : LK-KURAL")
        print("=" * 72)
        return 0

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
