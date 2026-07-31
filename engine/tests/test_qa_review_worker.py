from pathlib import Path

import pytest

from aidpl.qa_review_worker import (
    deterministic_gate,
    mock_review,
    transport_schema,
)


def test_transport_schema_is_strict() -> None:
    schema = transport_schema()

    assert schema["additionalProperties"] is False
    assert "verdict" in schema["required"]


def test_mock_review_blocks_publication() -> None:
    result = mock_review([])

    assert result["verdict"] == "REVIEW_REQUIRED"
    assert (
        result["publication_recommendation"]
        == "BLOCK_PUBLICATION"
    )


def test_deterministic_gate_detects_missing_case(
    tmp_path: Path,
) -> None:
    blockers = deterministic_gate(tmp_path)

    assert blockers
    assert any(
        "Missing artifact" in blocker
        for blocker in blockers
    )


def test_live_requires_authorization(tmp_path: Path) -> None:
    from aidpl.qa_review_worker import run_review

    with pytest.raises(
        ValueError,
        match="Live inference is disabled",
    ):
        run_review(
            case_id="LK-TEST",
            case_root=tmp_path,
            provider_name="openai",
            allow_live=False,
        )
