from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import validate

from .providers import ModelRequest, create_provider


ARTIFACTS = [
    ("01-metadata/metadata.json", "metadata.schema.json"),
    ("02-timeline/timeline.json", "timeline.schema.json"),
    ("03-facts/facts.json", "facts.schema.json"),
    ("04-issues/issues.json", "issues.schema.json"),
    ("05-evidence/evidence.json", "evidence.schema.json"),
]


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


def build_review_schema(
    schemas: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "metadata",
            "timeline",
            "facts",
            "issues",
            "evidence",
            "review_summary",
        ],
        "properties": {
            "metadata": schemas["metadata.schema.json"],
            "timeline": schemas["timeline.schema.json"],
            "facts": schemas["facts.schema.json"],
            "issues": schemas["issues.schema.json"],
            "evidence": schemas["evidence.schema.json"],
            "review_summary": {
                "type": "object",
                "required": [
                    "status",
                    "changes_made",
                    "uncertainties",
                ],
                "properties": {
                    "status": {"type": "string"},
                    "changes_made": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "uncertainties": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "additionalProperties": True,
            },
        },
        "additionalProperties": False,
    }


def build_mock_review(
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    reviewed: dict[str, Any] = {}

    mapping = {
        "metadata": "01-metadata/metadata.json",
        "timeline": "02-timeline/timeline.json",
        "facts": "03-facts/facts.json",
        "issues": "04-issues/issues.json",
        "evidence": "05-evidence/evidence.json",
    }

    for key, relative in mapping.items():
        payload = json.loads(json.dumps(artifacts[relative]))
        payload["status"] = "MODEL_REVIEWED_MOCK"
        payload.setdefault("quality_notes", [])
        payload["quality_notes"].append(
            "Mock provider reviewed structure only; no legal assertions added."
        )
        reviewed[key] = payload

    reviewed["review_summary"] = {
        "status": "MODEL_REVIEWED_MOCK",
        "changes_made": [
            "Updated artifact review status.",
            "Preserved deterministic content and traceability.",
        ],
        "uncertainties": [
            "Mock mode does not perform substantive legal review.",
        ],
    }

    return reviewed


def build_prompt(
    case_id: str,
    source_text: str,
    artifacts: dict[str, dict[str, Any]],
) -> tuple[str, str]:
    system_prompt = """You are the Legal Kural Legal Extraction Review Agent.

Review only the supplied judgment text and deterministic artifacts.

Rules:
1. Never invent facts, dates, evidence, parties, issues or holdings.
2. Distinguish allegations, submissions, undisputed facts and judicial findings.
3. Preserve page-level source traceability.
4. Return all five artifacts in the required JSON structure.
5. Use null or empty arrays when the judgment does not establish a value.
6. Mark uncertainty explicitly.
7. Do not provide legal advice or editorial commentary.
"""

    user_prompt = json.dumps(
        {
            "case_id": case_id,
            "task": (
                "Review and consolidate metadata, timeline, facts, "
                "issues and evidence."
            ),
            "source_text": source_text,
            "deterministic_artifacts": artifacts,
        },
        ensure_ascii=False,
    )

    return system_prompt, user_prompt


def validate_reviewed_artifacts(
    reviewed: dict[str, Any],
    schemas: dict[str, dict[str, Any]],
) -> None:
    mapping = {
        "metadata": "metadata.schema.json",
        "timeline": "timeline.schema.json",
        "facts": "facts.schema.json",
        "issues": "issues.schema.json",
        "evidence": "evidence.schema.json",
    }

    for key, schema_name in mapping.items():
        validate(
            instance=reviewed[key],
            schema=schemas[schema_name],
        )


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

    schemas = {
        schema_name: read_json(schema_root / schema_name)
        for _, schema_name in ARTIFACTS
    }

    artifacts = {
        relative: read_json(case_root / "output" / relative)
        for relative, _ in ARTIFACTS
    }

    provider = create_provider(provider_name)

    if provider_name == "mock":
        reviewed = build_mock_review(artifacts)
        response_metadata = {
            "provider": "mock",
            "model": provider.health()["model"],
            "request_id": "mock-extraction-review-0001",
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        }
    else:
        excerpt = source_excerpt(
            case_root / "working/source-text.txt",
            max_source_characters,
        )
        system_prompt, user_prompt = build_prompt(
            case_id,
            excerpt,
            artifacts,
        )
        review_schema = build_review_schema(schemas)

        response = provider.generate(
            ModelRequest(
                agent_id="LK-EXTRACT-REVIEW",
                task="Model-assisted legal extraction review",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                json_schema=review_schema,
                temperature=0.0,
                max_output_tokens=12000,
                metadata={
                    "case_id": case_id,
                    "agent": "LK-EXTRACT-REVIEW",
                },
            )
        )

        if not isinstance(response.structured, dict):
            raise ValueError(
                "Provider did not return a structured review object."
            )

        reviewed = response.structured
        response_metadata = {
            "provider": response.provider,
            "model": response.model,
            "request_id": response.request_id,
            "usage": response.usage,
        }

    validate_reviewed_artifacts(reviewed, schemas)

    backup_root = case_root / "working/pre-model-review"

    for relative, _ in ARTIFACTS:
        source_path = case_root / "output" / relative
        backup_path = backup_root / relative

        if not backup_path.exists():
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(
                source_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

    output_mapping = {
        "metadata": "01-metadata/metadata.json",
        "timeline": "02-timeline/timeline.json",
        "facts": "03-facts/facts.json",
        "issues": "04-issues/issues.json",
        "evidence": "05-evidence/evidence.json",
    }

    for key, relative in output_mapping.items():
        write_json(
            case_root / "output" / relative,
            reviewed[key],
        )

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-EXTRACT-REVIEW",
        "case_id": case_id,
        "status": (
            "COMPLETE_MOCK"
            if provider_name == "mock"
            else "COMPLETE_LIVE"
        ),
        "completed_at_utc": utc_now(),
        "provider": response_metadata,
        "review_summary": reviewed["review_summary"],
        "validated_artifacts": list(output_mapping.values()),
        "backup_root": str(backup_root),
        "live_inference": provider_name != "mock",
        "next_action": "RERUN_DOWNSTREAM_AGENTS",
    }

    write_json(
        case_root / "evidence/extraction-model-review-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-review-extract",
        description=(
            "Run model-assisted review of Legal Kural extraction artifacts."
        ),
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
        print("LEGAL KURAL MODEL-ASSISTED EXTRACTION REVIEW")
        print("=" * 76)
        print(f"Case        : {args.case_id}")
        print(f"Provider    : {report['provider']['provider']}")
        print(f"Model       : {report['provider']['model']}")
        print(f"Status      : {report['status']}")
        print("Artifacts   : 5 VALIDATED")
        print("Backup      : CREATED")
        print("Next Action : RERUN_DOWNSTREAM_AGENTS")
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
