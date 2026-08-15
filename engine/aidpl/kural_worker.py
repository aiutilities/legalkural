from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import validate

from .orchestrator import (
    complete_agent,
    load_plan,
    save_plan,
    start_agent,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact(value: str) -> str:
    return " ".join(value.split()).strip()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sentence(value: str, max_length: int = 320) -> str:
    cleaned = compact(value)

    if not cleaned:
        return ""

    match = re.match(r"(.+?[.!?])(?:\s|$)", cleaned)
    result = match.group(1) if match else cleaned

    if len(result) > max_length:
        result = result[:max_length].rsplit(" ", 1)[0].rstrip(" ,;:") + "."

    return result


def item_text(item: Any) -> str:
    if isinstance(item, str):
        return compact(item)

    if not isinstance(item, dict):
        return compact(str(item))

    for key in ("text", "question", "fact", "finding", "event"):
        value = item.get(key)
        if value:
            return compact(str(value))

    return compact(json.dumps(item, ensure_ascii=False))


def item_pages(item: Any) -> list[int]:
    if not isinstance(item, dict):
        return []

    pages = item.get("source_pages", [])
    return [page for page in pages if isinstance(page, int)]


def first_text(items: list[Any], fallback: str) -> str:
    for item in items:
        value = item_text(item)
        if value:
            return sentence(value)

    return fallback


def all_pages(*groups: list[Any]) -> list[int]:
    pages = set()

    for group in groups:
        for item in group:
            pages.update(item_pages(item))

    return sorted(pages)


def derive_title(
    issues: dict[str, Any],
    decision: dict[str, Any],
) -> str:
    outcome = decision.get("outcome")
    issue_items = issues.get("issues", [])

    issue_text = first_text(
        issue_items,
        "The law must follow the proven reality.",
    )

    lowered = issue_text.lower()

    if "residential" in lowered and "commercial" in lowered:
        return "Business Has a Name. Use Has a Nature."

    if "notice" in lowered or "natural justice" in lowered:
        return "No Burden Before a Hearing."

    if outcome == "Allowed":
        return "Reality Prevailed Over the Label."

    if outcome == "Dismissed":
        return "A Claim Fails Where Proof Fails."

    return "The Label Ends Where Reality Begins."


def derive_human_conflict(
    facts: dict[str, Any],
    issues: dict[str, Any],
) -> str:
    issue_text = first_text(
        issues.get("issues", []),
        "The parties disputed how the law should classify the facts.",
    )
    fact_text = first_text(
        facts.get("material_facts", []),
        "The judgment records competing accounts of the relevant activity.",
    )

    return (
        f"The human conflict arose because {fact_text.rstrip('.').lower()}, "
        f"while the legal dispute asked: {issue_text}"
    )


def derive_holding(
    reasoning: dict[str, Any],
    decision: dict[str, Any],
) -> str:
    ratio = first_text(
        reasoning.get("ratio_candidates", []),
        "",
    )

    if ratio:
        return ratio

    accepted_arguments = reasoning.get("accepted_arguments", [])

    for item in accepted_arguments:
        if not isinstance(item, dict):
            continue

        candidate = str(item.get("text") or "")
        lowered = candidate.lower()

        if (
            "end-use" in lowered
            or "actual use" in lowered
            or (
                "residential" in lowered
                and "commercial" in lowered
            )
        ):
            return candidate

    accepted = first_text(
        accepted_arguments,
        "",
    )

    if accepted:
        return accepted

    relief = first_text(
        decision.get("operative_directions", []),
        "",
    )

    if relief:
        return relief

    outcome = decision.get("outcome") or "undetermined"
    return f"The deterministic worker detected the outcome as {outcome}."


def derive_principle(
    holding: str,
    limitations: list[Any],
) -> str:
    lowered = holding.lower()

    if (
        "actual use" in lowered
        or "usage" in lowered
        or "end-use" in lowered
        or (
            "residential" in lowered
            and "commercial" in lowered
        )
    ):
        principle = (
            "Legal classification should follow proven functional use, "
            "not merely the label or commercial identity attached to it."
        )
    elif "natural justice" in lowered or "notice" in lowered:
        principle = (
            "Before the State increases a person's legal burden, "
            "it must provide notice and a fair opportunity to respond."
        )
    else:
        principle = (
            "A legal conclusion must follow verified facts, applicable law "
            "and fair procedure rather than assumption."
        )

    if limitations:
        principle += " Its application remains subject to the factual limits stated by the Court."

    return principle


def derive_english_kural(principle: str) -> str:
    lowered = principle.lower()

    if "functional use" in lowered:
        return "Labels may name the form; use reveals the truth."

    if "notice" in lowered or "opportunity" in lowered:
        return "A burden imposed unheard is justice left unfinished."

    return "Where proof leads, judgment must follow."


def build_brief(
    case_id: str,
    facts: dict[str, Any],
    issues: dict[str, Any],
    reasoning: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    limitations = decision.get("limitations", []) or reasoning.get(
        "limitations",
        [],
    )

    holding = derive_holding(reasoning, decision)
    principle = derive_principle(holding, limitations)

    fact_items = facts.get("material_facts", [])
    issue_items = issues.get("issues", [])
    ratio_items = reasoning.get("ratio_candidates", [])
    direction_items = decision.get("operative_directions", [])

    pages = all_pages(
        fact_items,
        issue_items,
        ratio_items,
        direction_items,
        limitations,
    )

    return {
        "schema_version": "1.0",
        "reference_case_id": case_id,
        "status": "EDITORIAL_DRAFT_REQUIRES_REVIEW",
        "compressed_title": derive_title(issues, decision),
        "human_conflict": derive_human_conflict(facts, issues),
        "legal_holding": holding,
        "universal_principle": principle,
        "kural_inspired_english": derive_english_kural(principle),
        "kural_inspired_tamil": None,
        "editorial_boundary": (
            "This draft separates the Court's legal holding from the "
            "editorial universal principle. It must not be published until "
            "a qualified editorial review verifies fidelity, nuance and "
            "the factual limits of the judgment."
        ),
        "source_traceability": [
            {
                "artifact": "facts",
                "source_pages": all_pages(fact_items),
            },
            {
                "artifact": "issues",
                "source_pages": all_pages(issue_items),
            },
            {
                "artifact": "reasoning",
                "source_pages": all_pages(ratio_items),
            },
            {
                "artifact": "decision",
                "source_pages": all_pages(
                    direction_items,
                    limitations,
                ),
            },
            {
                "artifact": "combined",
                "source_pages": pages,
            },
        ],
        "quality_notes": [
            "The English Kural-inspired line is an original machine draft.",
            "No generated line is presented as authentic Thirukkural.",
            "Tamil generation is intentionally disabled in deterministic mode.",
            "Human editorial review is mandatory before publication."
        ],
        "requires_human_editorial_review": True,
    }


def render_markdown(brief: dict[str, Any]) -> str:
    tamil = brief["kural_inspired_tamil"]

    tamil_section = (
        tamil
        if tamil
        else (
            "_Tamil Kural-inspired writing is pending human or "
            "model-assisted editorial review._"
        )
    )

    return f"""# {brief['compressed_title']}

**Reference Case:** {brief['reference_case_id']}

**Status:** Editorial Draft — Review Required

> This is original Legal Kural editorial writing. It is not an authentic
> Thirukkural verse.

## Human Conflict

{brief['human_conflict']}

## Legal Holding

{brief['legal_holding']}

## Universal Principle

{brief['universal_principle']}

## Kural-Inspired English

> **{brief['kural_inspired_english']}**

## Kural-Inspired Tamil

{tamil_section}

## Editorial Boundary

{brief['editorial_boundary']}

## Validation

- [x] Legal holding separated from editorial principle
- [x] Original writing disclaimer included
- [x] Source traceability preserved
- [ ] Legal fidelity review completed
- [ ] Tamil editorial review completed
- [ ] Founder approved
"""


def run_kural_generation(
    case_id: str,
    case_root: Path,
    schema_root: Path,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()

    facts = read_json(case_root / "output/03-facts/facts.json")
    issues = read_json(case_root / "output/04-issues/issues.json")
    reasoning = read_json(
        case_root / "output/07-reasoning/reasoning.json"
    )
    decision = read_json(
        case_root / "output/08-decision/decision.json"
    )

    brief = build_brief(
        case_id=case_id,
        facts=facts,
        issues=issues,
        reasoning=reasoning,
        decision=decision,
    )

    schema = json.loads(
        (schema_root / "kural.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=brief, schema=schema)

    output_dir = case_root / "output/09-kural"
    output_dir.mkdir(parents=True, exist_ok=True)

    brief_path = output_dir / "kural-brief.json"
    markdown_path = output_dir / "kural.md"

    write_json(brief_path, brief)
    markdown_path.write_text(
        render_markdown(brief).rstrip() + "\n",
        encoding="utf-8",
    )

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-KURAL",
        "case_id": case_id,
        "status": "COMPLETE_WITH_EDITORIAL_REVIEW_REQUIRED",
        "completed_at_utc": utc_now(),
        "outputs": [
            str(brief_path),
            str(markdown_path),
        ],
        "schema_validation": "PASS",
        "tamil_generation": "DEFERRED",
        "human_editorial_review_required": True,
        "next_agent": "LK-EDITOR",
    }

    write_json(
        case_root / "evidence/kural-generation-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-kural",
        description="Run the Legal Kural Reasoning Agent foundation.",
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
            start_agent(plan, "LK-KURAL")
            save_plan(args.plan, plan)

        root = Path(__file__).resolve().parents[2]
        report = run_kural_generation(
            case_id=args.case_id,
            case_root=args.case_root,
            schema_root=root / "engine/schemas",
        )

        if args.plan and plan is not None:
            plan = load_plan(args.plan)
            complete_agent(
                plan,
                "LK-KURAL",
                reviewer="AI-CEO",
                note=(
                    "Deterministic Kural brief and English editorial draft "
                    "created; human editorial review remains mandatory."
                ),
            )
            save_plan(args.plan, plan)

        print()
        print("=" * 72)
        print("LEGAL KURAL REASONING AGENT")
        print("=" * 72)
        print(f"Case          : {args.case_id}")
        print("Brief         : CREATED")
        print("Markdown      : CREATED")
        print("Schema        : PASS")
        print("Tamil         : DEFERRED")
        print("Human Review  : REQUIRED")
        print("Next Agent    : LK-EDITOR")
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
