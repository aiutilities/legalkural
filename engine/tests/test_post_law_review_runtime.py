from pathlib import Path

from aidpl.orchestrator import build_plan
from aidpl.post_law_review_runtime import reset_from_reason


def test_reset_from_reason(tmp_path: Path) -> None:
    plan = build_plan("LK-TEST", tmp_path)

    for agent in plan["agents"]:
        agent["status"] = "COMPLETE"
        agent["verdict"] = "PASS"

    reset_from_reason(plan)

    agents = {
        agent["agent_id"]: agent
        for agent in plan["agents"]
    }

    assert agents["LK-LAW"]["status"] == "COMPLETE"
    assert agents["LK-REASON"]["status"] == "READY"
    assert agents["LK-KURAL"]["status"] == "PENDING"
    assert plan["publication"]["qa_status"] == "PENDING"
