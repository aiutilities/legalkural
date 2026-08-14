from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
            "verdict",
            "confidence",
            "blocking_errors",
            "review_findings",
            "artifact_findings",
            "publication_recommendation",
        ],
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["PASS", "REVIEW_REQUIRED", "FAIL"],
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
            "blocking_errors": {
                "type": "array",
                "items": {"type": "string"},
            },
            "review_findings": {
                "type": "array",
                "items": {"type": "string"},
            },
            "artifact_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "artifact",
                        "status",
                        "findings",
                    ],
                    "properties": {
                        "artifact": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": [
                                "PASS",
                                "REVIEW_REQUIRED",
                                "FAIL",
                            ],
                        },
                        "findings": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "additionalProperties": False,
                },
            },
            "publication_recommendation": {
                "type": "string",
                "enum": [
                    "ALLOW_FOUNDER_REVIEW",
                    "BLOCK_PUBLICATION",
                ],
            },
        },
        "additionalProperties": False,
    }


def deterministic_gate(
    case_root: Path,
) -> list[str]:
    blockers: list[str] = []

    required_files = [
        "evidence/extraction-model-review-report.json",
        "evidence/law-model-review-report.json",
        "evidence/reasoning-model-review-report.json",
        "evidence/kural-model-review-report.json",
        "evidence/editorial-model-review-report.json",
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

    for relative in required_files:
        path = case_root / relative
        if not path.exists():
            blockers.append(f"Missing artifact: {relative}")
        elif path.stat().st_size == 0:
            blockers.append(f"Empty artifact: {relative}")

    article_path = case_root / "output/10-article/article.md"
    article = (
        article_path.read_text(encoding="utf-8")
        if article_path.exists()
        else ""
    )

    for phrase in [
        "not an authentic",
        "not personalised legal advice",
        "Founder",
        "Publication status",
    ]:
        if phrase.lower() not in article.lower():
            blockers.append(
                f"Article missing mandatory phrase: {phrase}"
            )

    return blockers


def build_prompt(
    case_id: str,
    artifacts: dict[str, Any],
) -> tuple[str, str]:
    system_prompt = """You are the independent Legal Kural Legal Fidelity and QA Review Agent.

Audit the complete case package before Founder review.

Rules:
1. Do not rewrite artifacts.
2. Check internal consistency across metadata, timeline, facts, issues, evidence, law, reasoning, decision, Kural brief and article.
3. Detect invented facts, unsupported propositions, incorrect legal authorities, contradictions, missing limitations and distorted holdings.
4. Distinguish legal fidelity defects from editorial preferences.
5. Treat Tamil Kural wording as requiring human language review unless independently verified.
6. A PASS means the package is safe to move to Founder review, not automatic publication.
7. Return FAIL only for material legal or structural defects.
8. Return REVIEW_REQUIRED for unresolved legal, Tamil, traceability or factual concerns.
9. Classify defects by their earliest true source. If an article exposes a missing, placeholder, incomplete, contradictory or unsupported upstream fact, issue, evidence item, authority, reasoning step or decision field, report the upstream source defect rather than describing it only as an editorial defect.
10. Do not treat an editorial placeholder as proof that LK-EDITOR owns the defect. Identify the earliest artifact that lacks the verified substance needed to replace the placeholder.
11. Reserve editorial findings for presentation, structure, wording or readability defects where the required verified substance already exists upstream.
12. Never approve publication directly.
"""

    user_prompt = json.dumps(
        {
            "case_id": case_id,
            "task": "Audit the full Legal Kural package.",
            "artifacts": artifacts,
        },
        ensure_ascii=False,
    )

    return system_prompt, user_prompt


def load_artifacts(case_root: Path) -> dict[str, Any]:
    output = case_root / "output"

    return {
        "metadata": read_json(
            output / "01-metadata/metadata.json"
        ),
        "timeline": read_json(
            output / "02-timeline/timeline.json"
        ),
        "facts": read_json(
            output / "03-facts/facts.json"
        ),
        "issues": read_json(
            output / "04-issues/issues.json"
        ),
        "evidence": read_json(
            output / "05-evidence/evidence.json"
        ),
        "law": read_json(
            output / "06-law/law.json"
        ),
        "reasoning": read_json(
            output / "07-reasoning/reasoning.json"
        ),
        "decision": read_json(
            output / "08-decision/decision.json"
        ),
        "kural": read_json(
            output / "09-kural/kural-brief.json"
        ),
        "article_markdown": (
            output / "10-article/article.md"
        ).read_text(encoding="utf-8"),
        "prior_validation": read_json(
            case_root / "evidence/validation-report.json"
        ),
    }


def mock_review(
    blockers: list[str],
) -> dict[str, Any]:
    verdict = "FAIL" if blockers else "REVIEW_REQUIRED"

    return {
        "verdict": verdict,
        "confidence": 1.0 if blockers else 0.5,
        "blocking_errors": blockers,
        "review_findings": [
            "Mock mode does not perform substantive legal QA."
        ],
        "artifact_findings": [],
        "publication_recommendation": "BLOCK_PUBLICATION",
    }


def run_review(
    case_id: str,
    case_root: Path,
    provider_name: str,
    allow_live: bool,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()

    if provider_name != "mock" and not allow_live:
        raise ValueError(
            "Live inference is disabled. Pass --allow-live explicitly."
        )

    blockers = deterministic_gate(case_root)

    if blockers:
        reviewed = {
            "verdict": "FAIL",
            "confidence": 1.0,
            "blocking_errors": blockers,
            "review_findings": [],
            "artifact_findings": [],
            "publication_recommendation": "BLOCK_PUBLICATION",
        }
        provider_metadata = {
            "provider": "deterministic-gate",
            "model": "none",
            "request_id": None,
            "usage": {},
        }
    else:
        artifacts = load_artifacts(case_root)
        provider = create_provider(provider_name)

        if provider_name == "mock":
            reviewed = mock_review(blockers)
            provider_metadata = {
                "provider": "mock",
                "model": provider.health()["model"],
                "request_id": "mock-qa-review-0001",
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                },
            }
        else:
            system_prompt, user_prompt = build_prompt(
                case_id,
                artifacts,
            )

            response = provider.generate(
                ModelRequest(
                    agent_id="LK-QA-REVIEW",
                    task="Model-assisted legal fidelity audit",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_format="json",
                    json_schema=transport_schema(),
                    temperature=0.0,
                    max_output_tokens=8000,
                    metadata={
                        "case_id": case_id,
                        "agent": "LK-QA-REVIEW",
                    },
                )
            )

            if not isinstance(response.structured, dict):
                raise ValueError(
                    "Provider did not return structured QA output."
                )

            reviewed = response.structured
            provider_metadata = {
                "provider": response.provider,
                "model": response.model,
                "request_id": response.request_id,
                "usage": response.usage,
            }

    verdict = reviewed["verdict"]
    publication_recommendation = reviewed[
        "publication_recommendation"
    ]

    if verdict != "PASS":
        publication_recommendation = "BLOCK_PUBLICATION"

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-QA-REVIEW",
        "case_id": case_id,
        "status": "COMPLETE",
        "completed_at_utc": utc_now(),
        "provider": provider_metadata,
        "verdict": verdict,
        "confidence": reviewed["confidence"],
        "blocking_errors": reviewed["blocking_errors"],
        "review_findings": reviewed["review_findings"],
        "artifact_findings": reviewed["artifact_findings"],
        "publication_recommendation": publication_recommendation,
        "founder_review_allowed": (
            verdict == "PASS"
            and publication_recommendation
            == "ALLOW_FOUNDER_REVIEW"
        ),
        "publication_ready": False,
        "next_action": (
            "FOUNDER_REVIEW"
            if verdict == "PASS"
            else "REMEDIATION_REQUIRED"
        ),
    }

    write_json(
        case_root / "evidence/qa-model-review-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-review-qa",
        description="Run independent model-assisted QA review.",
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
        print("LEGAL KURAL MODEL-ASSISTED QA REVIEW")
        print("=" * 76)
        print(f"Case        : {args.case_id}")
        print(f"Provider    : {report['provider']['provider']}")
        print(f"Model       : {report['provider']['model']}")
        print(f"Verdict     : {report['verdict']}")
        print(f"Confidence  : {report['confidence']:.2f}")
        print(
            f"Founder Gate: "
            f"{'OPEN' if report['founder_review_allowed'] else 'BLOCKED'}"
        )
        print(f"Next Action : {report['next_action']}")
        print("=" * 76)
        return 0 if report["verdict"] != "FAIL" else 1

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
