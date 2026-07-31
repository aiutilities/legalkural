from pathlib import Path

import pytest

from aidpl.orchestrator import (
    authorize_founder,
    build_plan,
    complete_agent,
    find_agent,
    refresh_readiness,
    start_agent,
)


def test_dependency_progression(tmp_path: Path) -> None:
    plan = build_plan("LK-TEST-0001", tmp_path)

    assert find_agent(plan, "LK-INTAKE")["status"] == "READY"
    assert find_agent(plan, "LK-EXTRACT")["status"] == "PENDING"

    start_agent(plan, "LK-INTAKE")
    complete_agent(plan, "LK-INTAKE", "LK-QA", None)

    assert find_agent(plan, "LK-EXTRACT")["status"] == "READY"


def test_agent_cannot_self_review(tmp_path: Path) -> None:
    plan = build_plan("LK-TEST-0002", tmp_path)
    start_agent(plan, "LK-INTAKE")

    with pytest.raises(ValueError, match="cannot review"):
        complete_agent(
            plan,
            "LK-INTAKE",
            "LK-INTAKE",
            None,
        )


def test_publication_requires_qa_and_founder(tmp_path: Path) -> None:
    plan = build_plan("LK-TEST-0003", tmp_path)

    for agent_id in [
        "LK-INTAKE",
        "LK-EXTRACT",
        "LK-LAW",
        "LK-REASON",
        "LK-KURAL",
        "LK-EDITOR",
        "LK-QA",
    ]:
        refresh_readiness(plan)
        start_agent(plan, agent_id)
        complete_agent(plan, agent_id, "AI-CEO", None)

    assert plan["publication"]["qa_status"] == "PASS"
    assert plan["publication"]["ready"] is False

    authorize_founder(plan)

    assert plan["publication"]["ready"] is True
