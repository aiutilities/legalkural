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
        complete_agent(
            plan,
            agent_id,
            "AI-CEO",
            None,
            verdict="PASS" if agent_id == "LK-QA" else None,
        )

    assert plan["publication"]["qa_status"] == "PASS"
    assert plan["publication"]["ready"] is False

    authorize_founder(plan)

    assert plan["publication"]["ready"] is True


def test_open_blocking_manual_task_prevents_agent_start(tmp_path):
    from aidpl.manual_tasks import create_task

    plan = build_plan("LK-GATE-001", tmp_path)

    create_task(
        case_root=tmp_path,
        case_id="LK-GATE-001",
        source_agent="TEST",
        task_type="KURAL_EDITORIAL_REVIEW",
        title="Human review required",
        instructions="Complete required human review.",
        blocking=True,
    )

    with pytest.raises(
        ValueError,
        match="OPEN blocking manual task",
    ):
        start_agent(plan, "LK-INTAKE")


def test_nonblocking_manual_task_does_not_prevent_agent_start(tmp_path):
    from aidpl.manual_tasks import create_task

    plan = build_plan("LK-GATE-002", tmp_path)

    create_task(
        case_root=tmp_path,
        case_id="LK-GATE-002",
        source_agent="TEST",
        task_type="KURAL_EDITORIAL_REVIEW",
        title="Nonblocking review",
        instructions="Review when convenient.",
        blocking=False,
    )

    start_agent(plan, "LK-INTAKE")

    assert find_agent(plan, "LK-INTAKE")["status"] == "IN_PROGRESS"


def test_completed_blocking_manual_task_does_not_prevent_agent_start(
    tmp_path,
):
    from aidpl.manual_tasks import complete_task, create_task

    plan = build_plan("LK-GATE-003", tmp_path)

    task = create_task(
        case_root=tmp_path,
        case_id="LK-GATE-003",
        source_agent="TEST",
        task_type="KURAL_EDITORIAL_REVIEW",
        title="Human review required",
        instructions="Complete required human review.",
        blocking=True,
    )

    complete_task(
        case_root=tmp_path,
        task_id=task["task_id"],
        completed_by="human-reviewer",
        completion_note="Review completed.",
    )

    start_agent(plan, "LK-INTAKE")

    assert find_agent(plan, "LK-INTAKE")["status"] == "IN_PROGRESS"


def test_assert_manual_execution_allowed_rejects_open_blocking_task(
    tmp_path,
):
    from aidpl.manual_tasks import create_task
    from aidpl.orchestrator import (
        assert_manual_execution_allowed,
    )

    plan = build_plan("LK-GATE-ASSERT-001", tmp_path)

    create_task(
        case_root=tmp_path,
        case_id="LK-GATE-ASSERT-001",
        task_type="LEGAL_FIDELITY_REVIEW",
        title="Human legal review required",
        instructions="Complete human legal review.",
        source_agent="TEST",
        blocking=True,
    )

    with pytest.raises(
        ValueError,
        match="OPEN blocking manual task prevents execution",
    ):
        assert_manual_execution_allowed(plan)
