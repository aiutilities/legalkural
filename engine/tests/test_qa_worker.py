import json
from pathlib import Path

from aidpl.orchestrator import (
    authorize_founder,
    build_plan,
    complete_agent,
    find_agent,
    refresh_readiness,
    start_agent,
)
from aidpl.qa_worker import REQUIRED_ARTIFACTS, run_qa


def create_case(root: Path, review_required: bool) -> None:
    for relative in REQUIRED_ARTIFACTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.suffix == ".json":
            status = (
                "REQUIRES_MODEL_REVIEW"
                if review_required
                else "VERIFIED"
            )
            path.write_text(
                json.dumps({"status": status}) + "\n",
                encoding="utf-8",
            )
        elif relative.endswith("kural.md"):
            path.write_text(
                "Not an authentic Thirukkural verse.\n",
                encoding="utf-8",
            )
        elif relative.endswith("article.md"):
            path.write_text(
                "Publication status: draft.\n"
                "This is not personalised legal advice.\n"
                "The Founder authorises publication.\n",
                encoding="utf-8",
            )
        else:
            path.write_text("content\n", encoding="utf-8")


def test_qa_review_required(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    create_case(case_root, review_required=True)

    report = run_qa("LK-QA-TEST-0001", case_root)

    assert report["verdict"] == "REVIEW_REQUIRED"
    assert report["publication_ready"] is False


def test_qa_pass(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    create_case(case_root, review_required=False)

    report = run_qa("LK-QA-TEST-0002", case_root)

    assert report["verdict"] == "PASS"
    assert report["publication_ready"] is True


def test_publication_uses_qa_verdict(tmp_path: Path) -> None:
    plan = build_plan("LK-QA-TEST-0003", tmp_path)

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
            reviewer="AI-CEO",
            note=None,
            verdict=(
                "REVIEW_REQUIRED"
                if agent_id == "LK-QA"
                else None
            ),
        )

    assert find_agent(plan, "LK-LEARN")["status"] == "READY"
    assert plan["publication"]["qa_status"] == "REVIEW_REQUIRED"
    assert plan["publication"]["ready"] is False

    authorize_founder(plan)
    assert plan["publication"]["ready"] is False
