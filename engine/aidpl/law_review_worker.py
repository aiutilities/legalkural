from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import validate

from .providers import ModelRequest, create_provider
from .schema_repair import repair_to_schema


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


def source_excerpt(path: Path, max_characters: int) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Source text missing: {path}")

    text = path.read_text(encoding="utf-8")

    if len(text) <= max_characters:
        return text

    half = max_characters // 2
    return (
        text[:half]
        + "\n\n[...SOURCE TRUNCATED FOR REVIEW...]\n\n"
        + text[-half:]
    )


def transport_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "law_json",
            "review_status",
            "changes_made",
            "uncertainties",
        ],
        "properties": {
            "law_json": {"type": "string"},
            "review_status": {"type": "string"},
            "changes_made": {
                "type": "array",
                "items": {"type": "string"},
            },
            "uncertainties": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "additionalProperties": False,
    }


def decode_live_review(transport: dict[str, Any]) -> dict[str, Any]:
    raw = transport.get("law_json")

    if not isinstance(raw, str):
        raise ValueError("Provider field law_json must be a JSON string.")

    try:
        law = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Provider field law_json contains invalid JSON.") from exc

    if not isinstance(law, dict):
        raise ValueError("Provider field law_json must decode to an object.")

    return {
        "law": law,
        "review_summary": {
            "status": transport["review_status"],
            "changes_made": transport["changes_made"],
            "uncertainties": transport["uncertainties"],
        },
    }


def mock_review(law: dict[str, Any]) -> dict[str, Any]:
    reviewed = json.loads(json.dumps(law))
    reviewed["status"] = "MODEL_REVIEWED_MOCK"
    reviewed.setdefault("quality_notes", [])
    reviewed["quality_notes"].append(
        "Mock provider reviewed structure only; no legal authority was added."
    )

    return {
        "law": reviewed,
        "review_summary": {
            "status": "MODEL_REVIEWED_MOCK",
            "changes_made": ["Updated review status only."],
            "uncertainties": [
                "Mock mode does not perform substantive legal analysis."
            ],
        },
    }


def build_prompt(
    case_id: str,
    source_text: str,
    facts: dict[str, Any],
    issues: dict[str, Any],
    law: dict[str, Any],
) -> tuple[str, str]:
    system_prompt = """You are the Legal Kural Legal Analysis Review Agent.

Review only the supplied judgment and structured artifacts.

Rules:
1. Never invent statutes, sections, rules, notifications or precedents.
2. Record how the Court used each legal authority.
3. Distinguish relied-on, discussed, distinguished, rejected and background authorities.
4. Preserve page-level source traceability.
5. Identify ratio and obiter only as candidates when uncertain.
6. Use empty arrays when the source does not establish a category.
7. Return the reviewed law artifact as a valid JSON-encoded string in law_json.
8. Do not provide personalised legal advice.
"""

    user_prompt = json.dumps(
        {
            "case_id": case_id,
            "task": "Review and consolidate the applicable-law artifact.",
            "source_text": source_text,
            "facts": facts,
            "issues": issues,
            "deterministic_law": law,
        },
        ensure_ascii=False,
    )

    return system_prompt, user_prompt


def run_review(
    case_id: str,
    case_root: Path,
    schema_root: Path,
    provider_name: str,
    max_source_characters: int,
    allow_live: bool,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()

    if provider_name != "mock" and not allow_live:
        raise ValueError(
            "Live inference is disabled. Pass --allow-live explicitly."
        )

    law_path = case_root / "output/06-law/law.json"
    law = read_json(law_path)
    facts = read_json(case_root / "output/03-facts/facts.json")
    issues = read_json(case_root / "output/04-issues/issues.json")
    schema = read_json(schema_root / "law.schema.json")

    provider = create_provider(provider_name)

    if provider_name == "mock":
        reviewed = mock_review(law)
        provider_metadata = {
            "provider": "mock",
            "model": provider.health()["model"],
            "request_id": "mock-law-review-0001",
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        }
    else:
        source_text = source_excerpt(
            case_root / "working/source-text.txt",
            max_source_characters,
        )
        system_prompt, user_prompt = build_prompt(
            case_id,
            source_text,
            facts,
            issues,
            law,
        )

        response = provider.generate(
            ModelRequest(
                agent_id="LK-LAW-REVIEW",
                task="Model-assisted legal analysis review",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                json_schema=transport_schema(),
                temperature=0.0,
                max_output_tokens=10000,
                metadata={
                    "case_id": case_id,
                    "agent": "LK-LAW-REVIEW",
                },
            )
        )

        if not isinstance(response.structured, dict):
            raise ValueError(
                "Provider did not return a structured law review object."
            )

        reviewed = decode_live_review(response.structured)
        provider_metadata = {
            "provider": response.provider,
            "model": response.model,
            "request_id": response.request_id,
            "usage": response.usage,
        }

    repair_result = repair_to_schema(
        provider=provider,
        agent_id="LK-LAW-SCHEMA-CRITIC",
        task="Repair the reviewed law artifact to its schema.",
        case_id=case_id,
        payload=reviewed["law"],
        schema=schema,
        max_attempts=2,
        max_output_tokens=12000,
    )
    reviewed["law"] = repair_result.payload

    validate(instance=reviewed["law"], schema=schema)

    backup_path = (
        case_root
        / "working/pre-law-model-review/06-law/law.json"
    )
    if not backup_path.exists():
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(
            law_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    write_json(law_path, reviewed["law"])

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-LAW-REVIEW",
        "case_id": case_id,
        "status": (
            "COMPLETE_MOCK"
            if provider_name == "mock"
            else "COMPLETE_LIVE"
        ),
        "completed_at_utc": utc_now(),
        "provider": provider_metadata,
        "review_summary": reviewed["review_summary"],
        "schema_repair": {
            "repaired": repair_result.repaired,
            "attempts": repair_result.attempts,
            "validation_errors": repair_result.validation_errors,
        },
        "validated_artifact": "06-law/law.json",
        "backup": str(backup_path),
        "live_inference": provider_name != "mock",
        "next_action": "RERUN_FROM_LK_REASON",
    }

    write_json(
        case_root / "evidence/law-model-review-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-review-law",
        description="Run model-assisted review of the law artifact.",
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai", "deepseek", "qwen"],
    )
    parser.add_argument(
        "--max-source-characters",
        type=int,
        default=80000,
    )
    parser.add_argument("--allow-live", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(__file__).resolve().parents[2]

    try:
        report = run_review(
            case_id=args.case_id,
            case_root=args.case_root,
            schema_root=root / "engine/schemas",
            provider_name=args.provider,
            max_source_characters=args.max_source_characters,
            allow_live=args.allow_live,
        )

        print()
        print("=" * 76)
        print("LEGAL KURAL MODEL-ASSISTED LAW REVIEW")
        print("=" * 76)
        print(f"Case        : {args.case_id}")
        print(f"Provider    : {report['provider']['provider']}")
        print(f"Model       : {report['provider']['model']}")
        print(f"Status      : {report['status']}")
        print("Artifact    : 06-law/law.json VALIDATED")
        print("Backup      : CREATED")
        print("Next Action : RERUN_FROM_LK_REASON")
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
