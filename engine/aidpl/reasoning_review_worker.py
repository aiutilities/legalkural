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
            "reasoning_json",
            "decision_json",
            "review_status",
            "changes_made",
            "uncertainties",
        ],
        "properties": {
            "reasoning_json": {"type": "string"},
            "decision_json": {"type": "string"},
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
    reviewed: dict[str, Any] = {}

    for output_name, transport_name in [
        ("reasoning", "reasoning_json"),
        ("decision", "decision_json"),
    ]:
        raw = transport.get(transport_name)

        if not isinstance(raw, str):
            raise ValueError(
                f"Provider field {transport_name} must be a JSON string."
            )

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Provider field {transport_name} contains invalid JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                f"Provider field {transport_name} must decode to an object."
            )

        reviewed[output_name] = parsed

    reviewed["review_summary"] = {
        "status": transport["review_status"],
        "changes_made": transport["changes_made"],
        "uncertainties": transport["uncertainties"],
    }

    return reviewed


def mock_review(
    reasoning: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    reviewed_reasoning = json.loads(json.dumps(reasoning))
    reviewed_decision = json.loads(json.dumps(decision))

    reviewed_reasoning["status"] = "MODEL_REVIEWED_MOCK"
    reviewed_decision["status"] = "MODEL_REVIEWED_MOCK"

    reviewed_reasoning.setdefault("quality_notes", []).append(
        "Mock provider reviewed structure only."
    )
    reviewed_decision.setdefault("quality_notes", []).append(
        "Mock provider reviewed structure only."
    )

    return {
        "reasoning": reviewed_reasoning,
        "decision": reviewed_decision,
        "review_summary": {
            "status": "MODEL_REVIEWED_MOCK",
            "changes_made": ["Updated review status only."],
            "uncertainties": [
                "Mock mode does not perform substantive judicial analysis."
            ],
        },
    }


def build_prompt(
    case_id: str,
    source_text: str,
    facts: dict[str, Any],
    issues: dict[str, Any],
    law: dict[str, Any],
    reasoning: dict[str, Any],
    decision: dict[str, Any],
) -> tuple[str, str]:
    system_prompt = """You are the Legal Kural Judicial Reasoning Review Agent.

Review only the supplied judgment and structured artifacts.

Rules:
1. Never invent reasoning, findings, relief, limitations or holdings.
2. Reconstruct the Court's issue-by-issue path from facts and law to conclusion.
3. Distinguish party submissions from judicial findings.
4. Distinguish accepted arguments, rejected arguments, ratio candidates and obiter candidates.
5. Preserve page-level traceability for every material conclusion.
6. Record the operative result exactly and preserve factual limitations.
7. Return reasoning and decision as valid JSON-encoded strings.
8. Use empty arrays where the source does not establish a category.
9. Do not provide personalised legal advice or editorial commentary.
"""

    user_prompt = json.dumps(
        {
            "case_id": case_id,
            "task": (
                "Review and consolidate judicial reasoning and decision."
            ),
            "source_text": source_text,
            "facts": facts,
            "issues": issues,
            "law": law,
            "deterministic_reasoning": reasoning,
            "deterministic_decision": decision,
        },
        ensure_ascii=False,
    )

    return system_prompt, user_prompt



def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _pages(item: Any) -> list[int]:
    if not isinstance(item, dict):
        return []

    values = (
        item.get("source_pages")
        or item.get("supporting_pages")
        or item.get("pages")
        or []
    )

    return [
        value
        for value in _as_list(values)
        if isinstance(value, int)
    ]


def _text_item(item: Any) -> dict[str, Any] | None:
    if isinstance(item, str):
        cleaned = " ".join(item.split())
        return {
            "text": cleaned,
            "source_pages": [],
            "status": "MODEL_REVIEWED",
        } if cleaned else None

    if not isinstance(item, dict):
        return None

    value = (
        item.get("text")
        or item.get("question")
        or item.get("conclusion")
        or item.get("finding")
        or item.get("usage")
    )

    if not value:
        return None

    return {
        "text": " ".join(str(value).split()),
        "source_pages": _pages(item),
        "status": "MODEL_REVIEWED",
    }


def _collect_items(values: Any) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []

    for value in _as_list(values):
        item = _text_item(value)
        if item:
            collected.append(item)

    return collected


def _deduplicate(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[int, ...]]] = set()

    for item in items:
        key = (
            item.get("text", ""),
            tuple(item.get("source_pages", [])),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result


def normalize_reasoning_contract(
    case_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    required = {
        "schema_version",
        "reference_case_id",
        "status",
        "issues",
        "reasoning_steps",
        "accepted_arguments",
        "rejected_arguments",
        "ratio_candidates",
        "limitations",
        "source_traceability",
    }

    if required.issubset(payload):
        normalized = json.loads(json.dumps(payload))
        normalized["reference_case_id"] = case_id
        return normalized

    normalized_issues: list[dict[str, Any]] = []
    reasoning_steps: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    ratio: list[dict[str, Any]] = []
    limitations: list[dict[str, Any]] = []

    for index, issue in enumerate(
        _as_list(payload.get("issues")),
        start=1,
    ):
        if not isinstance(issue, dict):
            continue

        question = issue.get("question") or issue.get("text")
        if question:
            issue_no = issue.get("issue_no", index)
            normalized_issues.append(
                {
                    "issue_id": (
                        f"I{int(issue_no):03d}"
                        if str(issue_no).isdigit()
                        else f"I{index:03d}"
                    ),
                    "question": " ".join(str(question).split()),
                    "source_pages": _pages(issue),
                    "status": "MODEL_REVIEWED",
                }
            )

        reasoning_steps.extend(
            _collect_items(issue.get("analysis_steps"))
        )
        reasoning_steps.extend(
            _collect_items(issue.get("court_findings"))
        )
        accepted.extend(
            _collect_items(issue.get("accepted_arguments"))
        )
        rejected.extend(
            _collect_items(issue.get("rejected_arguments"))
        )
        ratio.extend(
            _collect_items(issue.get("ratio_candidates"))
        )

    reasoning_steps.extend(
        _collect_items(payload.get("reasoning_steps"))
    )
    reasoning_steps.extend(
        _collect_items(payload.get("analysis_steps"))
    )
    accepted.extend(
        _collect_items(payload.get("accepted_arguments"))
    )
    rejected.extend(
        _collect_items(payload.get("rejected_arguments"))
    )
    ratio.extend(
        _collect_items(payload.get("ratio_candidates"))
    )
    limitations.extend(
        _collect_items(payload.get("limitations"))
    )
    limitations.extend(
        _collect_items(payload.get("scope_and_limitations"))
    )

    traceability: list[dict[str, Any]] = []

    for category, items in [
        ("issues", normalized_issues),
        ("reasoning_steps", reasoning_steps),
        ("accepted_arguments", accepted),
        ("rejected_arguments", rejected),
        ("ratio_candidates", ratio),
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
        "status": "MODEL_REVIEWED_LIVE",
        "issues": normalized_issues,
        "reasoning_steps": _deduplicate(reasoning_steps),
        "accepted_arguments": _deduplicate(accepted),
        "rejected_arguments": _deduplicate(rejected),
        "ratio_candidates": _deduplicate(ratio),
        "limitations": _deduplicate(limitations),
        "source_traceability": traceability,
        "quality_notes": [
            "OpenAI review normalized through AIDPL compatibility layer.",
            "Original model output preserved in evidence.",
        ],
    }


def normalize_decision_contract(
    case_id: str,
    payload: dict[str, Any],
    reasoning: dict[str, Any],
) -> dict[str, Any]:
    required = {
        "schema_version",
        "reference_case_id",
        "status",
        "outcome",
        "operative_directions",
        "relief_granted",
        "relief_denied",
        "costs",
        "limitations",
        "source_traceability",
    }

    if required.issubset(payload):
        normalized = json.loads(json.dumps(payload))
        normalized["reference_case_id"] = case_id
        return normalized

    outcome = (
        payload.get("outcome")
        or payload.get("result")
        or payload.get("disposition")
    )

    operative = _collect_items(
        payload.get("operative_directions")
        or payload.get("directions")
        or payload.get("orders")
        or payload.get("order")
    )
    granted = _collect_items(
        payload.get("relief_granted")
        or payload.get("granted_relief")
    )
    denied = _collect_items(
        payload.get("relief_denied")
        or payload.get("denied_relief")
    )
    limitations = _collect_items(
        payload.get("limitations")
        or payload.get("scope_and_limitations")
    )

    if not limitations:
        limitations = list(reasoning.get("limitations", []))

    if not outcome:
        joined = " ".join(
            item.get("text", "").lower()
            for item in operative
        )
        if "allowed" in joined:
            outcome = "Allowed"
        elif "dismissed" in joined:
            outcome = "Dismissed"
        elif "disposed" in joined:
            outcome = "Disposed"

    if not granted:
        granted = [
            item for item in operative
            if any(
                word in item.get("text", "").lower()
                for word in ("allowed", "quashed", "directed")
            )
        ]

    if not denied:
        denied = [
            item for item in operative
            if any(
                word in item.get("text", "").lower()
                for word in ("dismissed", "rejected", "denied")
            )
        ]

    costs_value = payload.get("costs")
    costs = (
        str(costs_value)
        if costs_value not in (None, "")
        else None
    )

    traceability = []

    for category, items in [
        ("operative_directions", operative),
        ("relief_granted", granted),
        ("relief_denied", denied),
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
        "status": "MODEL_REVIEWED_LIVE",
        "outcome": outcome,
        "operative_directions": _deduplicate(operative),
        "relief_granted": _deduplicate(granted),
        "relief_denied": _deduplicate(denied),
        "costs": costs,
        "limitations": _deduplicate(limitations),
        "source_traceability": traceability,
        "quality_notes": [
            "OpenAI decision review normalized through AIDPL compatibility layer.",
            "Original model output preserved in evidence.",
        ],
    }

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

    reasoning_path = (
        case_root / "output/07-reasoning/reasoning.json"
    )
    decision_path = (
        case_root / "output/08-decision/decision.json"
    )

    facts = read_json(case_root / "output/03-facts/facts.json")
    issues = read_json(case_root / "output/04-issues/issues.json")
    law = read_json(case_root / "output/06-law/law.json")
    reasoning = read_json(reasoning_path)
    decision = read_json(decision_path)

    reasoning_schema = read_json(
        schema_root / "reasoning.schema.json"
    )
    decision_schema = read_json(
        schema_root / "decision.schema.json"
    )

    provider = create_provider(provider_name)

    if provider_name == "mock":
        reviewed = mock_review(reasoning, decision)
        provider_metadata = {
            "provider": "mock",
            "model": provider.health()["model"],
            "request_id": "mock-reasoning-review-0001",
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
            reasoning,
            decision,
        )

        response = provider.generate(
            ModelRequest(
                agent_id="LK-REASON-REVIEW",
                task="Model-assisted judicial reasoning review",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                json_schema=transport_schema(),
                temperature=0.0,
                max_output_tokens=12000,
                metadata={
                    "case_id": case_id,
                    "agent": "LK-REASON-REVIEW",
                },
            )
        )

        if not isinstance(response.structured, dict):
            raise ValueError(
                "Provider did not return a structured reasoning review."
            )

        reviewed = decode_live_review(response.structured)

        write_json(
            case_root
            / "evidence/reasoning-model-raw-output.json",
            {
                "schema_version": "1.0",
                "case_id": case_id,
                "provider": response.provider,
                "model": response.model,
                "reasoning": reviewed["reasoning"],
                "decision": reviewed["decision"],
                "review_summary": reviewed["review_summary"],
            },
        )

        reviewed["reasoning"] = normalize_reasoning_contract(
            case_id,
            reviewed["reasoning"],
        )
        reviewed["decision"] = normalize_decision_contract(
            case_id,
            reviewed["decision"],
            reviewed["reasoning"],
        )

        provider_metadata = {
            "provider": response.provider,
            "model": response.model,
            "request_id": response.request_id,
            "usage": response.usage,
        }

    validate(
        instance=reviewed["reasoning"],
        schema=reasoning_schema,
    )
    validate(
        instance=reviewed["decision"],
        schema=decision_schema,
    )

    backup_root = (
        case_root / "working/pre-reasoning-model-review"
    )

    for source_path, relative in [
        (reasoning_path, "07-reasoning/reasoning.json"),
        (decision_path, "08-decision/decision.json"),
    ]:
        backup_path = backup_root / relative

        if not backup_path.exists():
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(
                source_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

    write_json(reasoning_path, reviewed["reasoning"])
    write_json(decision_path, reviewed["decision"])

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-REASON-REVIEW",
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
            "07-reasoning/reasoning.json",
            "08-decision/decision.json",
        ],
        "backup_root": str(backup_root),
        "live_inference": provider_name != "mock",
        "next_action": "RERUN_FROM_LK_KURAL",
    }

    write_json(
        case_root
        / "evidence/reasoning-model-review-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-review-reason",
        description=(
            "Run model-assisted review of reasoning and decision artifacts."
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
        print("LEGAL KURAL MODEL-ASSISTED REASONING REVIEW")
        print("=" * 76)
        print(f"Case        : {args.case_id}")
        print(f"Provider    : {report['provider']['provider']}")
        print(f"Model       : {report['provider']['model']}")
        print(f"Status      : {report['status']}")
        print("Artifacts   : 2 VALIDATED")
        print("Backup      : CREATED")
        print("Next Action : RERUN_FROM_LK_KURAL")
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
