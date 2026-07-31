import json

import pytest

from aidpl.providers.base import (
    ModelProvider,
    ModelRequest,
    ModelResponse,
)
from aidpl.schema_repair import (
    repair_to_schema,
    validation_message,
)


SCHEMA = {
    "type": "object",
    "required": [
        "schema_version",
        "reference_case_id",
        "status",
    ],
    "properties": {
        "schema_version": {"type": "string"},
        "reference_case_id": {"type": "string"},
        "status": {"type": "string"},
    },
}


class RepairProvider(ModelProvider):
    name = "repair-test"

    def generate(self, request: ModelRequest) -> ModelResponse:
        repaired = {
            "schema_version": "1.0",
            "reference_case_id": "LK-TEST",
            "status": "MODEL_REVIEWED",
        }

        return ModelResponse(
            provider=self.name,
            model="repair-test-v1",
            text="",
            structured={
                "repaired_json": json.dumps(repaired),
                "repair_notes": ["Added required contract fields."],
            },
            request_id="repair-1",
            usage={},
            raw={},
        )

    def health(self):
        return {"status": "READY"}


class BrokenProvider(RepairProvider):
    def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            provider=self.name,
            model="broken",
            text="",
            structured={
                "repaired_json": json.dumps({"still": "invalid"}),
                "repair_notes": [],
            },
            request_id="broken-1",
            usage={},
            raw={},
        )


def test_validation_message() -> None:
    error = validation_message({"status": "DRAFT"}, SCHEMA)
    assert error is not None
    assert "required property" in error


def test_valid_payload_skips_repair() -> None:
    payload = {
        "schema_version": "1.0",
        "reference_case_id": "LK-TEST",
        "status": "PASS",
    }

    result = repair_to_schema(
        provider=RepairProvider(),
        agent_id="TEST",
        task="Repair",
        case_id="LK-TEST",
        payload=payload,
        schema=SCHEMA,
    )

    assert result.repaired is False
    assert result.attempts == 0


def test_invalid_payload_is_repaired() -> None:
    result = repair_to_schema(
        provider=RepairProvider(),
        agent_id="TEST",
        task="Repair",
        case_id="LK-TEST",
        payload={"case_id": "LK-TEST"},
        schema=SCHEMA,
    )

    assert result.repaired is True
    assert result.attempts == 1
    assert result.payload["schema_version"] == "1.0"


def test_repair_stops_after_max_attempts() -> None:
    with pytest.raises(ValueError, match="Schema self-repair failed"):
        repair_to_schema(
            provider=BrokenProvider(),
            agent_id="TEST",
            task="Repair",
            case_id="LK-TEST",
            payload={"case_id": "LK-TEST"},
            schema=SCHEMA,
            max_attempts=2,
        )
