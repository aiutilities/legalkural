from pathlib import Path

from aidpl.orchestrator import build_plan
from aidpl.post_editorial_review_runtime import reset_from_qa


def test_reset_from_qa(tmp_path: Path) -> None:
    plan = build_plan("LK-TEST", tmp_path)

    for agent in plan["agents"]:
        agent["status"] = "COMPLETE"
        agent["verdict"] = "PASS"

    reset_from_qa(plan)

    agents = {
        agent["agent_id"]: agent
        for agent in plan["agents"]
    }

    assert agents["LK-EDITOR"]["status"] == "COMPLETE"
    assert agents["LK-QA"]["status"] == "READY"
    assert agents["LK-LEARN"]["status"] == "PENDING"
    assert plan["publication"]["qa_status"] == "PENDING"
