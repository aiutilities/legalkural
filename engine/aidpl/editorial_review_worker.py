from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .orchestrator import (
    assert_manual_execution_allowed,
    load_plan,
)
from .providers import ModelRequest, create_provider


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def transport_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "article_markdown",
            "review_status",
            "changes_made",
            "uncertainties",
            "legal_fidelity_notes",
            "editorial_notes",
        ],
        "properties": {
            "article_markdown": {"type": "string"},
            "review_status": {"type": "string"},
            "changes_made": {
                "type": "array",
                "items": {"type": "string"},
            },
            "uncertainties": {
                "type": "array",
                "items": {"type": "string"},
            },
            "legal_fidelity_notes": {
                "type": "array",
                "items": {"type": "string"},
            },
            "editorial_notes": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "additionalProperties": False,
    }


def mock_review(article: str) -> dict[str, Any]:
    return {
        "article_markdown": article,
        "review_summary": {
            "status": "MODEL_REVIEWED_MOCK",
            "changes_made": ["No content changes in mock mode."],
            "uncertainties": [
                "Mock mode does not perform substantive editorial review."
            ],
            "legal_fidelity_notes": [],
            "editorial_notes": [],
        },
    }


def decode_live_review(
    payload: dict[str, Any],
) -> dict[str, Any]:
    article = payload.get("article_markdown")

    if not isinstance(article, str) or not article.strip():
        raise ValueError(
            "Provider field article_markdown must be non-empty."
        )

    return {
        "article_markdown": article,
        "review_summary": {
            "status": payload["review_status"],
            "changes_made": payload["changes_made"],
            "uncertainties": payload["uncertainties"],
            "legal_fidelity_notes": payload[
                "legal_fidelity_notes"
            ],
            "editorial_notes": payload["editorial_notes"],
        },
    }



def normalize_article_structure(
    article: str,
    fallback_title: str,
) -> str:
    normalized = article.strip()

    heading_aliases = {
        "## Case Overview": "## Case Snapshot",
        "## Case at a Glance": "## Case Snapshot",
        "## The Case": "## What Is the Case About?",
        "## What the Case Is About": "## What Is the Case About?",
        "## Judicial Reasoning": "## How the Judge Reasoned",
        "## Court's Reasoning": "## How the Judge Reasoned",
        "## Court’s Reasoning": "## How the Judge Reasoned",
        "## Reasoning": "## How the Judge Reasoned",
        "## Outcome": "## The Decision",
        "## Final Decision": "## The Decision",
        "## Order": "## The Decision",
        "## Disclaimer": "## Editorial Disclaimer",
        "## Legal Disclaimer": "## Editorial Disclaimer",
    }

    for old, new in heading_aliases.items():
        normalized = normalized.replace(old, new)

    if not normalized.startswith("# "):
        normalized = f"# {fallback_title}\n\n" + normalized

    if "Publication status" not in normalized:
        parts = normalized.split("\n", 1)
        normalized = (
            parts[0]
            + "\n\n**Publication status:** Draft — QA and Founder approval required.\n"
            + ("\n" + parts[1] if len(parts) > 1 else "")
        )

    if "## Editorial Disclaimer" not in normalized:
        normalized += (
            "\n\n## Editorial Disclaimer\n\n"
            "This article is an educational explanation generated from "
            "structured legal artifacts. It is not personalised legal advice. "
            "Publication requires QA PASS and Founder authorisation.\n"
        )
    elif "not personalised legal advice" not in normalized.lower():
        normalized += (
            "\n\nThis article is not personalised legal advice. "
            "Founder authorisation is required before publication.\n"
        )

    return normalized.rstrip() + "\n"

def validate_article(article: str) -> list[str]:
    blockers: list[str] = []

    required_phrases = [
        "Publication status",
        "not personalised legal advice",
        "Founder",
    ]

    for phrase in required_phrases:
        if phrase.lower() not in article.lower():
            blockers.append(
                f"Required phrase missing: {phrase}"
            )

    required_sections = [
        "# ",
        "## Case Snapshot",
        "## What Is the Case About?",
        "## How the Judge Reasoned",
        "## The Decision",
        "## Editorial Disclaimer",
    ]

    for section in required_sections:
        if section not in article:
            blockers.append(
                f"Required section missing: {section}"
            )

    prohibited = (
        "Kural-Inspired Insight",
        "Kural-Inspired English",
        "Kural-Inspired Tamil",
    )
    for marker in prohibited:
        if marker.lower() in article.lower():
            blockers.append(f"TITLE_ONLY policy violation: {marker}")
    if re.search(r"[\u0B80-\u0BFF]", article):
        blockers.append("TITLE_ONLY policy violation: Tamil text")

    if len(article.split()) < 600:
        blockers.append(
            "Article is below the minimum 600-word editorial threshold."
        )

    return blockers


def build_prompt(
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
    article: str,
) -> tuple[str, str]:
    system_prompt = """You are the Legal Kural Legal Editorial Review Agent.

Rewrite the supplied draft into a legally faithful, readable journal article.

Rules:
1. Use only the supplied verified artifacts.
2. Never invent facts, dates, evidence, legal provisions, precedents or holdings.
3. Preserve the Court's reasoning, outcome and factual limitations.
4. Separate party submissions from judicial findings.
5. Explain legal terms in plain language without distorting them.
6. Write for citizens, law students and lawyers in one coherent article.
7. Preserve the source-grounded English title. The Thirukkural-inspired algorithm is TITLE_ONLY.
8. Do not create Tamil text, a couplet, verse, translation, transliteration, epigraph, subtitle, body paragraph or footer text. Preserve publication, legal-advice and Founder-approval disclaimers.
9. The reviewed article MUST contain these exact Markdown section headings:
   ## Case Snapshot
   ## What Is the Case About?
   ## How the Judge Reasoned
   ## The Decision
   ## Editorial Disclaimer
10. Each required substantive section must contain meaningful content grounded only in the supplied verified artifacts. Do not emit placeholder text, instructions to an editor, or statements that merely tell the reader to consult another artifact.
11. If the supplied artifacts do not contain enough verified substance to write a required section faithfully, do not invent the missing substance. Record the problem in uncertainties and legal_fidelity_notes. The downstream validator is intentionally fail-closed.
12. You may reorganize or consolidate the current draft to satisfy the canonical section structure, but preserve legally material substance and source-page traceability.
13. Target 1,500 to 2,500 words unless the source does not support that length.
14. Do not add citations outside the source page references already present in artifacts.
15. Return only the reviewed Markdown article in article_markdown plus review notes.
"""

    user_prompt = json.dumps(
        {
            "case_id": case_id,
            "task": "Review and rewrite the Legal Kural article.",
            "metadata": metadata,
            "timeline": timeline,
            "facts": facts,
            "issues": issues,
            "evidence": evidence,
            "law": law,
            "reasoning": reasoning,
            "decision": decision,
            "kural": kural,
            "current_article": article,
        },
        ensure_ascii=False,
    )

    return system_prompt, user_prompt


def run_review(
    case_id: str,
    case_root: Path,
    provider_name: str,
    allow_live: bool,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()

    plan_path = case_root / "aidpl-plan.json"
    if plan_path.exists():
        plan = load_plan(plan_path)
        assert_manual_execution_allowed(plan)

    if provider_name != "mock" and not allow_live:
        raise ValueError(
            "Live inference is disabled. Pass --allow-live explicitly."
        )

    output = case_root / "output"
    article_path = output / "10-article/article.md"

    metadata = read_json(output / "01-metadata/metadata.json")
    timeline = read_json(output / "02-timeline/timeline.json")
    facts = read_json(output / "03-facts/facts.json")
    issues = read_json(output / "04-issues/issues.json")
    evidence = read_json(output / "05-evidence/evidence.json")
    law = read_json(output / "06-law/law.json")
    reasoning = read_json(
        output / "07-reasoning/reasoning.json"
    )
    decision = read_json(
        output / "08-decision/decision.json"
    )
    kural = read_json(
        output / "09-kural/kural-brief.json"
    )

    article = article_path.read_text(encoding="utf-8")
    provider = create_provider(provider_name)

    if provider_name == "mock":
        reviewed = mock_review(article)
        provider_metadata = {
            "provider": "mock",
            "model": provider.health()["model"],
            "request_id": "mock-editorial-review-0001",
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        }
    else:
        system_prompt, user_prompt = build_prompt(
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
            article,
        )

        response = provider.generate(
            ModelRequest(
                agent_id="LK-EDITOR-REVIEW",
                task="Model-assisted legal editorial review",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                json_schema=transport_schema(),
                temperature=0.2,
                max_output_tokens=12000,
                metadata={
                    "case_id": case_id,
                    "agent": "LK-EDITOR-REVIEW",
                },
            )
        )

        if not isinstance(response.structured, dict):
            raise ValueError(
                "Provider did not return a structured editorial review."
            )

        reviewed = decode_live_review(response.structured)
        reviewed["article_markdown"] = normalize_article_structure(
            reviewed["article_markdown"],
            fallback_title=str(
                kural.get("compressed_title")
                or "Legal Kural Case Analysis"
            ),
        )
        provider_metadata = {
            "provider": response.provider,
            "model": response.model,
            "request_id": response.request_id,
            "usage": response.usage,
        }

        write_json(
            case_root
            / "evidence/editorial-model-raw-output.json",
            {
                "schema_version": "1.0",
                "case_id": case_id,
                "provider": response.provider,
                "model": response.model,
                "article_markdown": reviewed[
                    "article_markdown"
                ],
                "review_summary": reviewed[
                    "review_summary"
                ],
            },
        )

    blockers = validate_article(
        reviewed["article_markdown"]
    )

    if blockers:
        raise ValueError(
            "Reviewed article failed editorial validation: "
            + "; ".join(blockers)
        )

    backup_path = (
        case_root
        / "working/pre-editorial-model-review/"
        "10-article/article.md"
    )

    if not backup_path.exists():
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(
            article,
            encoding="utf-8",
        )

    article_path.write_text(
        reviewed["article_markdown"].rstrip() + "\n",
        encoding="utf-8",
    )

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-EDITOR-REVIEW",
        "case_id": case_id,
        "status": (
            "COMPLETE_MOCK"
            if provider_name == "mock"
            else "COMPLETE_LIVE"
        ),
        "completed_at_utc": utc_now(),
        "provider": provider_metadata,
        "review_summary": reviewed["review_summary"],
        "validated_artifact": "10-article/article.md",
        "backup": str(backup_path),
        "word_count": len(
            reviewed["article_markdown"].split()
        ),
        "live_inference": provider_name != "mock",
        "next_action": "RERUN_FROM_LK_QA",
    }

    write_json(
        case_root
        / "evidence/editorial-model-review-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-review-editor",
        description="Run model-assisted editorial review.",
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai", "deepseek", "qwen"],
    )
    parser.add_argument("--allow-live", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        report = run_review(
            case_id=args.case_id,
            case_root=args.case_root,
            provider_name=args.provider,
            allow_live=args.allow_live,
        )

        print()
        print("=" * 76)
        print("LEGAL KURAL MODEL-ASSISTED EDITORIAL REVIEW")
        print("=" * 76)
        print(f"Case        : {args.case_id}")
        print(f"Provider    : {report['provider']['provider']}")
        print(f"Model       : {report['provider']['model']}")
        print(f"Status      : {report['status']}")
        print(f"Words       : {report['word_count']}")
        print("Article     : VALIDATED")
        print("Next Action : RERUN_FROM_LK_QA")
        print("=" * 76)
        return 0

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
