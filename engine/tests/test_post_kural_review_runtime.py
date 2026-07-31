from pathlib import Path

from aidpl.orchestrator import build_plan
from aidpl.post_kural_review_runtime import reset_from_editor


def test_reset_from_editor(tmp_path: Path) -> None:
    plan = build_plan("LK-TEST", tmp_path)

    for agent in plan["agents"]:
        agent["status"] = "COMPLETE"
        agent["verdict"] = "PASS"

    reset_from_editor(plan)

    agents = {
        agent["agent_id"]: agent
        for agent in plan["agents"]
    }

    assert agents["LK-KURAL"]["status"] == "COMPLETE"
    assert agents["LK-EDITOR"]["status"] == "READY"
    assert agents["LK-QA"]["status"] == "PENDING"
    assert plan["publication"]["qa_status"] == "PENDING"
