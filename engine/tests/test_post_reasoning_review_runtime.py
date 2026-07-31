from pathlib import Path

from aidpl.orchestrator import build_plan
from aidpl.post_reasoning_review_runtime import reset_from_kural


def test_reset_from_kural(tmp_path: Path) -> None:
    plan = build_plan("LK-TEST", tmp_path)

    for agent in plan["agents"]:
        agent["status"] = "COMPLETE"
        agent["verdict"] = "PASS"

    reset_from_kural(plan)

    agents = {
        agent["agent_id"]: agent
        for agent in plan["agents"]
    }

    assert agents["LK-REASON"]["status"] == "COMPLETE"
    assert agents["LK-KURAL"]["status"] == "READY"
    assert agents["LK-EDITOR"]["status"] == "PENDING"
    assert plan["publication"]["qa_status"] == "PENDING"
