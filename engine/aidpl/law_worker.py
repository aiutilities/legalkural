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


ARTICLE_PATTERN = re.compile(
    r"\bArticle\s+(\d+[A-Z]?)\b",
    re.IGNORECASE,
)

SECTION_PATTERN = re.compile(
    r"\bSection\s+(\d+[A-Z]?(?:\([^)]+\))?)\s+of\s+"
    r"(?:the\s+)?([A-Z][A-Za-z0-9 ,.'&()/-]{3,120}?"
    r"(?:Act|Code|Constitution)(?:,\s*\d{4})?)",
    re.IGNORECASE,
)

REGULATION_PATTERN = re.compile(
    r"\bRegulation\s+(\d+(?:\([^)]+\))?)\s+of\s+"
    r"([A-Z][A-Za-z0-9 ,.'&()/-]{3,140}?Regulations(?:,\s*\d{4})?)",
    re.IGNORECASE,
)

NOTIFICATION_PATTERN = re.compile(
    r"\bNotification\s+No\.?\s*([A-Za-z0-9./()-]+)"
    r"(?:\s+dated\s+([A-Za-z0-9 ,.-]+))?",
    re.IGNORECASE,
)

CASE_CITATION_PATTERNS = [
    re.compile(
        r"\b([A-Z][A-Za-z .&()'-]{2,100}\s+v\.?\s+"
        r"[A-Z][A-Za-z .&()'-]{2,100})"
        r"\s*,?\s*(\[[12]\d{3}\][^\n,;]{0,80})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b([A-Z][A-Za-z .&()'-]{2,100}\s+v\.?\s+"
        r"[A-Z][A-Za-z .&()'-]{2,100})"
        r"\s*\((?:Civil|Criminal|Writ|C\.A\.|W\.P\.)"
        r"[^)\n]{0,120}\)",
        re.IGNORECASE,
    ),
]

DOCTRINE_TERMS = {
    "principles of natural justice": "Principles of Natural Justice",
    "alternate remedy": "Alternative Remedy",
    "alternative remedy": "Alternative Remedy",
    "purposive interpretation": "Purposive Interpretation",
    "beneficial interpretation": "Beneficial Interpretation",
    "literal interpretation": "Literal Interpretation",
    "reasonable classification": "Reasonable Classification",
    "equality before law": "Equality Before Law",
    "audi alteram partem": "Audi Alteram Partem",
    "ratio decidendi": "Ratio Decidendi",
    "obiter dicta": "Obiter Dicta",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def compact(value: str) -> str:
    return " ".join(value.split()).strip(" ,.;")


def add_unique(
    target: list[dict[str, Any]],
    seen: set[tuple[Any, ...]],
    key: tuple[Any, ...],
    item: dict[str, Any],
) -> None:
    if key in seen:
        return

    seen.add(key)
    target.append(item)


def extract_context(
    text: str,
    start: int,
    end: int,
    width: int = 180,
) -> str:
    return compact(
        text[max(0, start - width):min(len(text), end + width)]
    )


def extract_law_map(
    case_id: str,
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    constitutional: list[dict[str, Any]] = []
    statutes: list[dict[str, Any]] = []
    regulations: list[dict[str, Any]] = []
    notifications: list[dict[str, Any]] = []
    precedents: list[dict[str, Any]] = []
    doctrines: list[dict[str, Any]] = []
    traceability: list[dict[str, Any]] = []

    constitutional_seen: set[tuple[Any, ...]] = set()
    statute_seen: set[tuple[Any, ...]] = set()
    regulation_seen: set[tuple[Any, ...]] = set()
    notification_seen: set[tuple[Any, ...]] = set()
    precedent_seen: set[tuple[Any, ...]] = set()
    doctrine_seen: set[tuple[Any, ...]] = set()

    for page in pages:
        page_no = page["page"]
        text = page["text"]

        for match in ARTICLE_PATTERN.finditer(text):
            article = match.group(1).upper()
            item = {
                "provision": f"Article {article}",
                "context": extract_context(
                    text,
                    match.start(),
                    match.end(),
                ),
                "source_pages": [page_no],
                "status": "CANDIDATE",
            }
            add_unique(
                constitutional,
                constitutional_seen,
                (article,),
                item,
            )

        for match in SECTION_PATTERN.finditer(text):
            section = compact(match.group(1))
            statute = compact(match.group(2))
            item = {
                "name": statute,
                "provision": f"Section {section}",
                "context": extract_context(
                    text,
                    match.start(),
                    match.end(),
                ),
                "source_pages": [page_no],
                "status": "CANDIDATE",
            }
            add_unique(
                statutes,
                statute_seen,
                (statute.lower(), section.lower()),
                item,
            )

        for match in REGULATION_PATTERN.finditer(text):
            provision = compact(match.group(1))
            regulation = compact(match.group(2))
            item = {
                "name": regulation,
                "provision": f"Regulation {provision}",
                "context": extract_context(
                    text,
                    match.start(),
                    match.end(),
                ),
                "source_pages": [page_no],
                "status": "CANDIDATE",
            }
            add_unique(
                regulations,
                regulation_seen,
                (regulation.lower(), provision.lower()),
                item,
            )

        for match in NOTIFICATION_PATTERN.finditer(text):
            number = compact(match.group(1))
            date = compact(match.group(2) or "")
            item = {
                "number": number,
                "date_text": date or None,
                "context": extract_context(
                    text,
                    match.start(),
                    match.end(),
                ),
                "source_pages": [page_no],
                "status": "CANDIDATE",
            }
            add_unique(
                notifications,
                notification_seen,
                (number.lower(), date.lower()),
                item,
            )

        for pattern in CASE_CITATION_PATTERNS:
            for match in pattern.finditer(text):
                case_name = compact(match.group(1))

                citation = (
                    compact(match.group(2))
                    if match.lastindex and match.lastindex >= 2
                    else None
                )

                item = {
                    "case": case_name,
                    "citation": citation,
                    "context": extract_context(
                        text,
                        match.start(),
                        match.end(),
                    ),
                    "source_pages": [page_no],
                    "treatment": "CANDIDATE",
                }
                add_unique(
                    precedents,
                    precedent_seen,
                    (
                        case_name.lower(),
                        (citation or "").lower(),
                    ),
                    item,
                )

        lowered = text.lower()

        for term, doctrine_name in DOCTRINE_TERMS.items():
            if term not in lowered:
                continue

            index = lowered.index(term)
            item = {
                "name": doctrine_name,
                "context": extract_context(
                    text,
                    index,
                    index + len(term),
                ),
                "source_pages": [page_no],
                "status": "CANDIDATE",
            }
            add_unique(
                doctrines,
                doctrine_seen,
                (doctrine_name.lower(),),
                item,
            )

    for category, items in [
        ("constitutional_provisions", constitutional),
        ("statutes", statutes),
        ("regulations", regulations),
        ("notifications", notifications),
        ("precedents", precedents),
        ("legal_doctrines", doctrines),
    ]:
        for item in items:
            traceability.append(
                {
                    "category": category,
                    "identifier": (
                        item.get("provision")
                        or item.get("name")
                        or item.get("number")
                        or item.get("case")
                    ),
                    "source_pages": item["source_pages"],
                }
            )

    ratio_candidates = []

    for page in pages:
        text = page["text"]
        lowered = text.lower()

        markers = [
            "this court is of the considered view",
            "this court holds",
            "we hold",
            "accordingly",
            "in view of the above",
        ]

        for marker in markers:
            start = 0

            while True:
                index = lowered.find(marker, start)

                if index < 0:
                    break

                ratio_candidates.append(
                    {
                        "text": extract_context(
                            text,
                            index,
                            index + len(marker),
                            width=260,
                        ),
                        "source_pages": [page["page"]],
                        "status": "CANDIDATE",
                    }
                )
                start = index + len(marker)

    return {
        "schema_version": "1.0",
        "reference_case_id": case_id,
        "status": "REQUIRES_MODEL_REVIEW",
        "constitutional_provisions": constitutional,
        "statutes": statutes,
        "regulations": regulations,
        "notifications": notifications,
        "precedents": precedents,
        "legal_doctrines": doctrines,
        "ratio_candidates": ratio_candidates[:30],
        "obiter_candidates": [],
        "source_traceability": traceability,
        "quality_notes": [
            "Legal authorities were detected deterministically.",
            "Citation normalization remains pending.",
            "Treatment of precedents requires model-assisted review.",
            "Ratio and obiter classification requires legal review."
        ]
    }


def validate_artifact(
    artifact: dict[str, Any],
    schema_path: Path,
) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=artifact, schema=schema)


def run_law_analysis(
    case_id: str,
    case_root: Path,
    schema_root: Path,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()
    pages = load_pages(case_root / "working/source-text.txt")

    artifact = extract_law_map(case_id, pages)
    schema_path = schema_root / "law.schema.json"

    validate_artifact(artifact, schema_path)

    output_path = case_root / "output/06-law/law.json"
    write_json(output_path, artifact)

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-LAW",
        "case_id": case_id,
        "status": "COMPLETE_WITH_MODEL_REVIEW_REQUIRED",
        "completed_at_utc": utc_now(),
        "page_count": len(pages),
        "output": str(output_path),
        "schema": "law.schema.json",
        "schema_validation": "PASS",
        "counts": {
            "constitutional_provisions": len(
                artifact["constitutional_provisions"]
            ),
            "statutes": len(artifact["statutes"]),
            "regulations": len(artifact["regulations"]),
            "notifications": len(artifact["notifications"]),
            "precedents": len(artifact["precedents"]),
            "legal_doctrines": len(artifact["legal_doctrines"]),
            "ratio_candidates": len(artifact["ratio_candidates"]),
        },
        "model_review_required": True,
        "next_agent": "LK-REASON",
    }

    write_json(
        case_root / "evidence/law-analysis-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-law",
        description="Run deterministic Legal Analysis Agent foundation.",
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
            start_agent(plan, "LK-LAW")
            save_plan(args.plan, plan)

        root = Path(__file__).resolve().parents[2]
        report = run_law_analysis(
            case_id=args.case_id,
            case_root=args.case_root,
            schema_root=root / "engine/schemas",
        )

        if args.plan and plan is not None:
            plan = load_plan(args.plan)
            complete_agent(
                plan,
                "LK-LAW",
                reviewer="AI-CEO",
                note=(
                    "Deterministic legal-authority mapping and schema "
                    "validation passed; model review remains required."
                ),
            )
            save_plan(args.plan, plan)

        print()
        print("=" * 72)
        print("LEGAL KURAL LEGAL ANALYSIS AGENT")
        print("=" * 72)
        print(f"Case        : {args.case_id}")
        print(f"Pages       : {report['page_count']}")
        print(f"Statutes    : {report['counts']['statutes']}")
        print(f"Regulations : {report['counts']['regulations']}")
        print(f"Precedents  : {report['counts']['precedents']}")
        print(f"Doctrines   : {report['counts']['legal_doctrines']}")
        print("Schema      : PASS")
        print("Model Review: REQUIRED")
        print("Next Agent  : LK-REASON")
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
