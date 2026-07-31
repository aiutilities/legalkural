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


PAGE_PATTERN = re.compile(
    r"<PAGE:(?P<number>\d+)>\n(?P<text>.*?)\n</PAGE:(?P=number)>",
    re.DOTALL,
)

CASE_NUMBER_PATTERN = re.compile(
    r"\bW\.P\.No?s?\."
    r"\s*[\d,\s&]+"
    r"\s+of\s+\d{4}\b",
    re.IGNORECASE,
)

DATE_PATTERNS = {
    "reserved_on": re.compile(
        r"Reserved\s+on\s+(\d{2}\.\d{2}\.\d{4})",
        re.IGNORECASE,
    ),
    "pronounced_on": re.compile(
        r"Pronounced\s+on\s+(\d{2}\.\d{2}\.?\d{4})",
        re.IGNORECASE,
    ),
}

ISSUE_PATTERN = re.compile(
    r"(?:main\s+issues?|Issue\s+No\.\s*\d+).*?"
    r"(Whether.*?)(?=\n\s*\d+\.|\n\s*Issue\s+No\.|\Z)",
    re.IGNORECASE | re.DOTALL,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_pages(source_text: Path) -> list[dict[str, Any]]:
    if not source_text.exists():
        raise FileNotFoundError(f"Source text missing: {source_text}")

    text = source_text.read_text(encoding="utf-8")
    pages = []

    for match in PAGE_PATTERN.finditer(text):
        pages.append(
            {
                "page": int(match.group("number")),
                "text": match.group("text").strip(),
            }
        )

    if not pages:
        raise ValueError("No page markers found in source text.")

    return pages


def parse_date(raw: str | None) -> str | None:
    if not raw:
        return None

    normalized = raw.replace("..", ".").strip(".")
    day, month, year = normalized.split(".")
    return f"{year}-{month}-{day}"


def first_page_matching(
    pages: list[dict[str, Any]],
    pattern: re.Pattern[str],
) -> int | None:
    for page in pages:
        if pattern.search(page["text"]):
            return page["page"]
    return None


def extract_metadata(
    case_id: str,
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    full_text = "\n".join(page["text"] for page in pages)
    title_text = "\n".join(page["text"] for page in pages[:3])

    court = None
    if "HIGH COURT OF JUDICATURE AT MADRAS" in title_text.upper():
        court = "High Court of Judicature at Madras"

    judge_match = re.search(
        r"THE HON'?BLE\s+(?:MR\.?\s+)?JUSTICE\s+([A-Z .]+)",
        title_text,
        re.IGNORECASE,
    )
    judge = " ".join(judge_match.group(1).split()).title() if judge_match else None

    case_numbers = sorted(
        {
            " ".join(match.group(0).split())
            for match in CASE_NUMBER_PATTERN.finditer(full_text)
        }
    )

    dates: dict[str, str | None] = {}
    traceability = []

    for key, pattern in DATE_PATTERNS.items():
        match = pattern.search(full_text)
        dates[key] = parse_date(match.group(1)) if match else None

        page = first_page_matching(pages, pattern)
        if page:
            traceability.append(
                {
                    "field": key,
                    "source_pages": [page],
                }
            )

    return {
        "schema_version": "1.0",
        "reference_case_id": case_id,
        "status": "DRAFT_DETERMINISTIC",
        "court": court,
        "judge": judge,
        "case_numbers": case_numbers,
        "dates": dates,
        "source_traceability": traceability,
        "quality_notes": [
            "Deterministic extraction only.",
            "Legal Extraction Agent model review is still required."
        ]
    }


def extract_timeline(
    case_id: str,
    pages: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    events = []

    if metadata["dates"]["reserved_on"]:
        events.append(
            {
                "date": metadata["dates"]["reserved_on"],
                "event": "Judgment reserved",
                "source_pages": [
                    first_page_matching(
                        pages,
                        DATE_PATTERNS["reserved_on"],
                    )
                ],
            }
        )

    if metadata["dates"]["pronounced_on"]:
        events.append(
            {
                "date": metadata["dates"]["pronounced_on"],
                "event": "Judgment pronounced",
                "source_pages": [
                    first_page_matching(
                        pages,
                        DATE_PATTERNS["pronounced_on"],
                    )
                ],
            }
        )

    for page in pages:
        for match in re.finditer(
            r"\bdated\s+(\d{2}\.\d{2}\.\d{4})",
            page["text"],
            re.IGNORECASE,
        ):
            date = parse_date(match.group(1))
            event = page["text"][
                max(0, match.start() - 100):
                min(len(page["text"]), match.end() + 100)
            ]
            events.append(
                {
                    "date": date,
                    "event": " ".join(event.split()),
                    "source_pages": [page["page"]],
                }
            )

    unique = []
    seen = set()

    for event in events:
        key = (
            event["date"],
            event["event"],
            tuple(event["source_pages"]),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)

    return {
        "schema_version": "1.0",
        "reference_case_id": case_id,
        "status": "DRAFT_DETERMINISTIC",
        "events": unique,
        "quality_notes": [
            "Timeline contains detected dates only.",
            "Chronology requires Legal Extraction Agent review."
        ]
    }


def extract_facts(
    case_id: str,
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_facts = []

    fact_terms = (
        "petitioners have been",
        "in these cases",
        "the inmates",
        "the respondents had",
        "no documentary evidence",
    )

    for page in pages:
        sentences = re.split(r"(?<=[.!?])\s+", page["text"])

        for sentence in sentences:
            normalized = " ".join(sentence.split())
            lowered = normalized.lower()

            if len(normalized) < 40:
                continue

            if any(term in lowered for term in fact_terms):
                candidate_facts.append(
                    {
                        "text": normalized,
                        "source_pages": [page["page"]],
                        "classification": "CANDIDATE_FACT",
                    }
                )

    return {
        "schema_version": "1.0",
        "reference_case_id": case_id,
        "status": "REQUIRES_MODEL_REVIEW",
        "material_facts": candidate_facts[:40],
        "undisputed_facts": [],
        "disputed_facts": [],
        "quality_notes": [
            "Candidates were selected lexically.",
            "Fact, allegation and judicial finding separation is pending."
        ]
    }


def extract_issues(
    case_id: str,
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    full_text = "\n".join(page["text"] for page in pages)
    issues = []

    for match in ISSUE_PATTERN.finditer(full_text):
        issue = " ".join(match.group(1).split())
        if len(issue) > 500:
            issue = issue[:500].rstrip() + "..."

        page = first_page_matching(
            pages,
            re.compile(re.escape(issue[:40]), re.IGNORECASE),
        )

        issues.append(
            {
                "question": issue,
                "source_pages": [page] if page else [],
                "status": "CANDIDATE",
            }
        )

    if not issues:
        for page in pages:
            for line in page["text"].splitlines():
                cleaned = " ".join(line.split())
                if cleaned.lower().startswith("whether "):
                    issues.append(
                        {
                            "question": cleaned,
                            "source_pages": [page["page"]],
                            "status": "CANDIDATE",
                        }
                    )

    return {
        "schema_version": "1.0",
        "reference_case_id": case_id,
        "status": "REQUIRES_MODEL_REVIEW",
        "issues": issues[:20],
        "quality_notes": [
            "Issue wording is extracted from source where detectable.",
            "Issue consolidation and court answer are pending."
        ]
    }


def extract_evidence(
    case_id: str,
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    documentary = []
    electronic = []
    missing = []

    evidence_terms = {
        "demand notice": "Demand or recovery notice",
        "property tax demand": "Property tax demand",
        "website": "Online municipal assessment record",
        "documentary evidence": "Documentary evidence",
    }

    for page in pages:
        lowered = page["text"].lower()

        for term, label in evidence_terms.items():
            if term in lowered:
                item = {
                    "title": label,
                    "source_pages": [page["page"]],
                    "status": "CANDIDATE",
                }

                target = electronic if term == "website" else documentary
                if item not in target:
                    target.append(item)

        if (
            "no documentary evidence" in lowered
            or "no documentary evidences" in lowered
        ):
            missing.append(
                {
                    "title": "Proof identified as absent by the Court",
                    "source_pages": [page["page"]],
                    "status": "CANDIDATE",
                }
            )

    return {
        "schema_version": "1.0",
        "reference_case_id": case_id,
        "status": "REQUIRES_MODEL_REVIEW",
        "documentary_evidence": documentary,
        "electronic_evidence": electronic,
        "missing_evidence": missing,
        "quality_notes": [
            "Evidence categories are lexical candidates.",
            "Purpose, admissibility and judicial treatment are pending."
        ]
    }


def validate_artifact(
    artifact: dict[str, Any],
    schema_path: Path,
) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=artifact, schema=schema)


def run_extraction(
    case_id: str,
    case_root: Path,
    schema_root: Path,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()
    source_text = case_root / "working/source-text.txt"

    pages = load_pages(source_text)

    metadata = extract_metadata(case_id, pages)
    timeline = extract_timeline(case_id, pages, metadata)
    facts = extract_facts(case_id, pages)
    issues = extract_issues(case_id, pages)
    evidence = extract_evidence(case_id, pages)

    artifacts = [
        (
            "01-metadata/metadata.json",
            metadata,
            "metadata.schema.json",
        ),
        (
            "02-timeline/timeline.json",
            timeline,
            "timeline.schema.json",
        ),
        (
            "03-facts/facts.json",
            facts,
            "facts.schema.json",
        ),
        (
            "04-issues/issues.json",
            issues,
            "issues.schema.json",
        ),
        (
            "05-evidence/evidence.json",
            evidence,
            "evidence.schema.json",
        ),
    ]

    validation_results = []

    for relative_path, payload, schema_name in artifacts:
        schema_path = schema_root / schema_name
        validate_artifact(payload, schema_path)

        output_path = case_root / "output" / relative_path
        write_json(output_path, payload)

        validation_results.append(
            {
                "artifact": relative_path,
                "schema": schema_name,
                "status": "PASS",
            }
        )

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-EXTRACT",
        "case_id": case_id,
        "status": "COMPLETE_WITH_MODEL_REVIEW_REQUIRED",
        "completed_at_utc": utc_now(),
        "page_count": len(pages),
        "artifacts": validation_results,
        "next_agent": "LK-LAW",
        "model_review_required": True,
    }

    write_json(
        case_root / "evidence/extraction-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-extract",
        description="Run deterministic Legal Extraction Agent foundation.",
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
            start_agent(plan, "LK-EXTRACT")
            save_plan(args.plan, plan)

        root = Path(__file__).resolve().parents[2]
        report = run_extraction(
            case_id=args.case_id,
            case_root=args.case_root,
            schema_root=root / "engine/schemas",
        )

        if args.plan and plan is not None:
            plan = load_plan(args.plan)
            complete_agent(
                plan,
                "LK-EXTRACT",
                reviewer="AI-CEO",
                note=(
                    "Deterministic extraction and schema validation passed; "
                    "model review remains required."
                ),
            )
            save_plan(args.plan, plan)

        print()
        print("=" * 72)
        print("LEGAL KURAL EXTRACTION AGENT")
        print("=" * 72)
        print(f"Case        : {args.case_id}")
        print(f"Pages       : {report['page_count']}")
        print("Artifacts   : 5")
        print("Schemas     : PASS")
        print("Model Review: REQUIRED")
        print("Next Agent  : LK-LAW")
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
