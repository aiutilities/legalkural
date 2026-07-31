from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError, validate

from .providers import ModelProvider, ModelRequest


@dataclass(frozen=True)
class RepairResult:
    payload: dict[str, Any]
    repaired: bool
    attempts: int
    validation_errors: list[str]


def validation_message(
    payload: dict[str, Any],
    schema: dict[str, Any],
) -> str | None:
    try:
        validate(instance=payload, schema=schema)
        return None
    except ValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path)
        return f"{path or '<root>'}: {exc.message}"


def repair_transport_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["repaired_json", "repair_notes"],
        "properties": {
            "repaired_json": {"type": "string"},
            "repair_notes": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "additionalProperties": False,
    }


def repair_to_schema(
    *,
    provider: ModelProvider,
    agent_id: str,
    task: str,
    case_id: str,
    payload: dict[str, Any],
    schema: dict[str, Any],
    max_attempts: int = 2,
    max_output_tokens: int = 12000,
) -> RepairResult:
    error = validation_message(payload, schema)

    if error is None:
        return RepairResult(payload, False, 0, [])

    current = payload
    errors = [error]

    for attempt in range(1, max_attempts + 1):
        response = provider.generate(
            ModelRequest(
                agent_id=agent_id,
                task=task,
                system_prompt=(
                    "Repair only the JSON structure so it validates against "
                    "the supplied schema. Do not add facts, dates, legal "
                    "authorities, findings, holdings or conclusions. Preserve "
                    "supported content. Return the complete repaired object as "
                    "a JSON-encoded string in repaired_json."
                ),
                user_prompt=json.dumps(
                    {
                        "case_id": case_id,
                        "validation_error": errors[-1],
                        "authoritative_schema": schema,
                        "invalid_payload": current,
                    },
                    ensure_ascii=False,
                ),
                response_format="json",
                json_schema=repair_transport_schema(),
                temperature=0.0,
                max_output_tokens=max_output_tokens,
                metadata={
                    "case_id": case_id,
                    "agent": agent_id,
                    "repair_attempt": str(attempt),
                },
            )
        )

        if not isinstance(response.structured, dict):
            errors.append("Repair provider returned no structured response.")
            continue

        raw = response.structured.get("repaired_json")

        if not isinstance(raw, str):
            errors.append("Repair provider omitted repaired_json.")
            continue

        try:
            repaired = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"Repair response contained invalid JSON: {exc}")
            continue

        if not isinstance(repaired, dict):
            errors.append("Repair response did not decode to an object.")
            continue

        current = repaired
        error = validation_message(current, schema)

        if error is None:
            return RepairResult(
                payload=current,
                repaired=True,
                attempts=attempt,
                validation_errors=errors,
            )

        errors.append(error)

    raise ValueError(
        "Schema self-repair failed after "
        f"{max_attempts} attempts: {' | '.join(errors)}"
    )
