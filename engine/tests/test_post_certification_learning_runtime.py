import copy

import pytest

from aidpl.orchestrator import (
    build_plan,
    find_agent,
    refresh_readiness,
)
from aidpl.post_certification_learning_runtime import (
    prepare_post_certification_learning,
)


def certified_plan(tmp_path):
    plan = build_plan(
        "LK-POST-CERT-TEST-0001",
        tmp_path / "case",
    )

    for agent in plan["agents"]:
        agent["status"] = "COMPLETE"
        agent["started_at_utc"] = "old-start"
        agent["completed_at_utc"] = "old-complete"
        agent["reviewed_by"] = "AI-CEO"
        agent["verdict"] = None
        agent["notes"] = ["Historical execution."]

    qa = find_agent(plan, "LK-QA")
    qa["verdict"] = "PASS"

    plan["publication"]["qa_status"] = "PASS"
    plan["publication"]["founder_authorization"] = "AUTHORIZED"
    plan["publication"]["ready"] = True

    refresh_readiness(plan)
    return plan


def certified_qa():
    return {
        "verdict": "PASS",
        "publication_ready": True,
        "next_agent": "LK-LEARN",
    }


def test_prepare_fresh_learning_preserves_certified_agents(
    tmp_path,
):
    plan = certified_plan(tmp_path)

    before = {
        agent["agent_id"]: copy.deepcopy(agent)
        for agent in plan["agents"]
        if agent["agent_id"] != "LK-LEARN"
    }

    old_learn = copy.deepcopy(
        find_agent(plan, "LK-LEARN")
    )

    previous = prepare_post_certification_learning(
        plan,
        certified_qa(),
    )

    learn = find_agent(plan, "LK-LEARN")

    assert previous == old_learn
    assert learn["status"] == "READY"
    assert learn["dependencies"] == ["LK-QA"]
    assert learn["started_at_utc"] is None
    assert learn["completed_at_utc"] is None
    assert learn["reviewed_by"] is None

    for agent_id, historical in before.items():
        assert find_agent(plan, agent_id) == historical

    assert plan["publication"]["qa_status"] == "PASS"
    assert (
        plan["publication"]["founder_authorization"]
        == "AUTHORIZED"
    )
    assert plan["publication"]["ready"] is True


@pytest.mark.parametrize(
    "qa",
    [
        {
            "verdict": "REVIEW_REQUIRED",
            "publication_ready": False,
            "next_agent": "LK-LEARN",
        },
        {
            "verdict": "PASS",
            "publication_ready": False,
            "next_agent": "LK-LEARN",
        },
        {
            "verdict": "PASS",
            "publication_ready": True,
            "next_agent": "LK-EDITOR",
        },
    ],
)
def test_prepare_learning_fails_closed_on_uncertified_qa(
    tmp_path,
    qa,
):
    plan = certified_plan(tmp_path)

    with pytest.raises(ValueError):
        prepare_post_certification_learning(plan, qa)


def test_prepare_learning_requires_completed_qa(tmp_path):
    plan = certified_plan(tmp_path)
    find_agent(plan, "LK-QA")["status"] = "READY"

    with pytest.raises(ValueError):
        prepare_post_certification_learning(
            plan,
            certified_qa(),
        )
