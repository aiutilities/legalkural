from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import validate

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
            "kural_json",
            "kural_markdown",
            "review_status",
            "changes_made",
            "uncertainties",
        ],
        "properties": {
            "kural_json": {"type": "string"},
            "kural_markdown": {"type": "string"},
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
    raw_json = transport.get("kural_json")
    markdown = transport.get("kural_markdown")

    if not isinstance(raw_json, str):
        raise ValueError(
            "Provider field kural_json must be a JSON string."
        )

    if not isinstance(markdown, str):
        raise ValueError(
            "Provider field kural_markdown must be a string."
        )

    try:
        kural = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Provider field kural_json contains invalid JSON."
        ) from exc

    if not isinstance(kural, dict):
        raise ValueError(
            "Provider field kural_json must decode to an object."
        )

    return {
        "kural": kural,
        "markdown": markdown,
        "review_summary": {
            "status": transport["review_status"],
            "changes_made": transport["changes_made"],
            "uncertainties": transport["uncertainties"],
        },
    }


def normalize_legal_holding(value: Any) -> str:
    """Normalize model-supplied legal holding into publication-safe prose.

    The model may return either a plain string or a structured object.
    Structured holdings are flattened deterministically instead of being
    stringified as Python dict syntax.
    """
    if value in (None, ""):
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        preferred_order = (
            "classification_and_tariff",
            "natural_justice_and_maintainability",
            "operative_limits",
        )

        parts: list[str] = []

        for key in preferred_order:
            item = value.get(key)
            if item not in (None, ""):
                parts.append(str(item).strip())

        for key, item in value.items():
            if key in preferred_order:
                continue
            if item not in (None, ""):
                parts.append(str(item).strip())

        return " ".join(
            part
            for part in parts
            if part
        )

    if isinstance(value, list):
        return " ".join(
            str(item).strip()
            for item in value
            if item not in (None, "")
        )

    return str(value)


def normalize_kural_contract(
    case_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    normalized = {
        "schema_version": str(
            payload.get("schema_version") or "1.0"
        ),
        "reference_case_id": case_id,
        "status": str(
            payload.get("status")
            or "MODEL_REVIEWED_LIVE"
        ),
        "compressed_title": str(
            payload.get("compressed_title")
            or payload.get("title")
            or "Legal Meaning Beyond the Label"
        ),
        "human_conflict": str(
            payload.get("human_conflict")
            or payload.get("conflict")
            or ""
        ),
        "legal_holding": normalize_legal_holding(
            payload.get("legal_holding")
            or payload.get("holding")
        ),
        "universal_principle": str(
            payload.get("universal_principle")
            or payload.get("principle")
            or ""
        ),
        "kural_inspired_english": str(
            payload.get("kural_inspired_english")
            or payload.get("english_kural")
            or ""
        ),
        "kural_inspired_tamil": (
            str(
                payload.get("kural_inspired_tamil")
                or payload.get("tamil_kural")
            )
            if (
                payload.get("kural_inspired_tamil")
                or payload.get("tamil_kural")
            )
            else None
        ),
        "editorial_boundary": str(
            payload.get("editorial_boundary")
            or (
                "This is original Legal Kural editorial writing. "
                "It is not an authentic Thirukkural verse and must "
                "not be represented as one."
            )
        ),
        "source_traceability": (
            payload.get("source_traceability")
            if isinstance(
                payload.get("source_traceability"),
                list,
            )
            else []
        ),
        "quality_notes": (
            payload.get("quality_notes")
            if isinstance(
                payload.get("quality_notes"),
                list,
            )
            else []
        ),
        "requires_human_editorial_review": bool(
            payload.get(
                "requires_human_editorial_review",
                True,
            )
        ),
    }

    normalized["status"] = "MODEL_REVIEWED_LIVE"
    normalized["requires_human_editorial_review"] = True

    normalized["quality_notes"].extend(
        [
            "OpenAI Kural review normalized through AIDPL.",
            "Tamil and English lines are original editorial writing.",
            "Neither line may be represented as authentic Thirukkural.",
            "Human Tamil and legal-fidelity review remain mandatory.",
        ]
    )

    return normalized


def render_fallback_markdown(
    kural: dict[str, Any],
) -> str:
    tamil = (
        kural["kural_inspired_tamil"]
        or "_Tamil editorial line requires human review._"
    )

    return f"""# {kural['compressed_title']}

**Reference Case:** {kural['reference_case_id']}

> This is original Legal Kural editorial writing. It is not an authentic
> Thirukkural verse.

## Human Conflict

{kural['human_conflict']}

## Legal Holding

{kural['legal_holding']}

## Universal Principle

{kural['universal_principle']}

## Kural-Inspired English

> **{kural['kural_inspired_english']}**

## Kural-Inspired Tamil

> **{tamil}**

## Editorial Boundary

{kural['editorial_boundary']}

## Review Gate

- [x] OpenAI Kural review completed
- [ ] Legal fidelity review completed
- [ ] Tamil language review completed
- [ ] Founder approval recorded
"""


def mock_review(
    current: dict[str, Any],
    markdown: str,
) -> dict[str, Any]:
    reviewed = json.loads(json.dumps(current))
    reviewed["status"] = "MODEL_REVIEWED_MOCK"
    reviewed["requires_human_editorial_review"] = True
    reviewed.setdefault("quality_notes", []).append(
        "Mock provider reviewed structure only."
    )

    return {
        "kural": reviewed,
        "markdown": markdown,
        "review_summary": {
            "status": "MODEL_REVIEWED_MOCK",
            "changes_made": ["Updated review status only."],
            "uncertainties": [
                "Mock mode does not perform substantive editorial review."
            ],
        },
    }


def build_prompt(
    case_id: str,
    facts: dict[str, Any],
    issues: dict[str, Any],
    reasoning: dict[str, Any],
    decision: dict[str, Any],
    current: dict[str, Any],
) -> tuple[str, str]:
    system_prompt = """You are the Legal Kural Kural Reasoning Review Agent.

Transform the verified legal reasoning into concise, humane editorial insight.

Rules:
1. Preserve the Court's legal holding exactly in substance.
2. Clearly separate the legal holding from the universal principle.
3. Create one compressed title.
4. Create one original English Kural-inspired line.
5. Create one original Tamil Kural-inspired couplet only when confident.
6. Never present generated writing as authentic Thirukkural.
7. Avoid invented facts, moral overreach and legal advice.
8. Preserve factual limits and source traceability.
9. Human Tamil and legal review remain mandatory.
10. Return the reviewed object as JSON in kural_json and the full
    publication-ready draft section in kural_markdown.
"""

    user_prompt = json.dumps(
        {
            "case_id": case_id,
            "task": (
                "Review and improve the Legal Kural editorial brief "
                "without changing the judicial holding."
            ),
            "facts": facts,
            "issues": issues,
            "reasoning": reasoning,
            "decision": decision,
            "current_kural": current,
        },
        ensure_ascii=False,
    )

    return system_prompt, user_prompt


def run_review(
    case_id: str,
    case_root: Path,
    schema_root: Path,
    provider_name: str,
    allow_live: bool,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()

    if provider_name != "mock" and not allow_live:
        raise ValueError(
            "Live inference is disabled. Pass --allow-live explicitly."
        )

    output_root = case_root / "output"
    kural_path = output_root / "09-kural/kural-brief.json"
    markdown_path = output_root / "09-kural/kural.md"

    facts = read_json(output_root / "03-facts/facts.json")
    issues = read_json(output_root / "04-issues/issues.json")
    reasoning = read_json(
        output_root / "07-reasoning/reasoning.json"
    )
    decision = read_json(
        output_root / "08-decision/decision.json"
    )
    current = read_json(kural_path)
    current_markdown = markdown_path.read_text(encoding="utf-8")

    schema = read_json(schema_root / "kural.schema.json")
    provider = create_provider(provider_name)

    if provider_name == "mock":
        reviewed = mock_review(current, current_markdown)
        provider_metadata = {
            "provider": "mock",
            "model": provider.health()["model"],
            "request_id": "mock-kural-review-0001",
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        }
    else:
        system_prompt, user_prompt = build_prompt(
            case_id,
            facts,
            issues,
            reasoning,
            decision,
            current,
        )

        response = provider.generate(
            ModelRequest(
                agent_id="LK-KURAL-REVIEW",
                task="Model-assisted Kural editorial review",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                json_schema=transport_schema(),
                temperature=0.2,
                max_output_tokens=6000,
                metadata={
                    "case_id": case_id,
                    "agent": "LK-KURAL-REVIEW",
                },
            )
        )

        if not isinstance(response.structured, dict):
            raise ValueError(
                "Provider did not return a structured Kural review."
            )

        reviewed = decode_live_review(response.structured)

        write_json(
            case_root
            / "evidence/kural-model-raw-output.json",
            {
                "schema_version": "1.0",
                "case_id": case_id,
                "provider": response.provider,
                "model": response.model,
                "kural": reviewed["kural"],
                "markdown": reviewed["markdown"],
                "review_summary": reviewed["review_summary"],
            },
        )

        reviewed["kural"] = normalize_kural_contract(
            case_id,
            reviewed["kural"],
        )

        if (
            "not an authentic" not in
            reviewed["markdown"].lower()
        ):
            reviewed["markdown"] = render_fallback_markdown(
                reviewed["kural"]
            )

        provider_metadata = {
            "provider": response.provider,
            "model": response.model,
            "request_id": response.request_id,
            "usage": response.usage,
        }

    validate(instance=reviewed["kural"], schema=schema)

    backup_root = (
        case_root / "working/pre-kural-model-review/09-kural"
    )
    backup_root.mkdir(parents=True, exist_ok=True)

    backup_json = backup_root / "kural-brief.json"
    backup_markdown = backup_root / "kural.md"

    if not backup_json.exists():
        backup_json.write_text(
            kural_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    if not backup_markdown.exists():
        backup_markdown.write_text(
            current_markdown,
            encoding="utf-8",
        )

    write_json(kural_path, reviewed["kural"])
    markdown_path.write_text(
        reviewed["markdown"].rstrip() + "\n",
        encoding="utf-8",
    )

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-KURAL-REVIEW",
        "case_id": case_id,
        "status": (
            "COMPLETE_MOCK"
            if provider_name == "mock"
            else "COMPLETE_LIVE"
        ),
        "completed_at_utc": utc_now(),
        "provider": provider_metadata,
        "review_summary": reviewed["review_summary"],
        "validated_artifacts": [
            "09-kural/kural-brief.json",
            "09-kural/kural.md",
        ],
        "backup_root": str(backup_root),
        "live_inference": provider_name != "mock",
        "human_tamil_review_required": True,
        "next_action": "RERUN_FROM_LK_EDITOR",
    }

    write_json(
        case_root / "evidence/kural-model-review-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-review-kural",
        description="Run model-assisted review of Kural artifacts.",
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
    root = Path(__file__).resolve().parents[2]

    try:
        report = run_review(
            case_id=args.case_id,
            case_root=args.case_root,
            schema_root=root / "engine/schemas",
            provider_name=args.provider,
            allow_live=args.allow_live,
        )

        print()
        print("=" * 76)
        print("LEGAL KURAL MODEL-ASSISTED KURAL REVIEW")
        print("=" * 76)
        print(f"Case        : {args.case_id}")
        print(f"Provider    : {report['provider']['provider']}")
        print(f"Model       : {report['provider']['model']}")
        print(f"Status      : {report['status']}")
        print("Artifacts   : 2 VALIDATED")
        print("Tamil Gate  : HUMAN REVIEW REQUIRED")
        print("Next Action : RERUN_FROM_LK_EDITOR")
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
