from pathlib import Path

from aidpl.orchestrator import build_plan
from aidpl.review_runtime import reset_downstream, worker_command


def test_reset_downstream(tmp_path: Path) -> None:
    plan = build_plan("LK-REVIEW-TEST-0001", tmp_path)

    for agent in plan["agents"]:
        agent["status"] = "COMPLETE"
        agent["reviewed_by"] = "AI-CEO"
        agent["verdict"] = "PASS"

    plan["publication"]["qa_status"] = "PASS"
    plan["publication"]["ready"] = True

    reset_downstream(plan)

    agents = {
        agent["agent_id"]: agent
        for agent in plan["agents"]
    }

    assert agents["LK-INTAKE"]["status"] == "COMPLETE"
    assert agents["LK-EXTRACT"]["status"] == "COMPLETE"
    assert agents["LK-LAW"]["status"] == "READY"

    for agent_id in [
        "LK-REASON",
        "LK-KURAL",
        "LK-EDITOR",
        "LK-QA",
        "LK-LEARN",
    ]:
        assert agents[agent_id]["status"] == "PENDING"

    assert plan["publication"]["qa_status"] == "PENDING"
    assert plan["publication"]["ready"] is False


def test_worker_command(tmp_path: Path) -> None:
    command = worker_command(
        root=tmp_path,
        worker="aidpl-law",
        case_id="LK-REVIEW-TEST-0002",
        case_root=tmp_path / "case",
        plan_path=tmp_path / "case/aidpl-plan.json",
    )

    assert command[0].endswith("bin/aidpl-law")
    assert "--case-id" in command
    assert "--plan" in command
