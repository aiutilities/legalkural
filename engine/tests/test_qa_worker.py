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



def test_qa_accepts_founder_approval_equivalent(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    create_case(case_root, review_required=False)

    article_path = case_root / "output/10-article/article.md"
    article = article_path.read_text(encoding="utf-8")

    article = article.replace(
        "Founder authorises publication",
        "Founder approval",
    )

    article_path.write_text(article, encoding="utf-8")

    report = run_qa("LK-QA-TEST-FOUNDER", case_root)

    assert not any(
        "Founder authorises publication" in error
        for error in report["blocking_errors"]
    )


def test_qa_ignores_superseded_stage_review_markers(
    tmp_path: Path,
) -> None:
    case_root = tmp_path / "case"
    create_case(case_root, review_required=False)

    historical_statuses = {
        "evidence/extraction-report.json":
            "COMPLETE_WITH_MODEL_REVIEW_REQUIRED",
        "evidence/law-analysis-report.json":
            "COMPLETE_WITH_MODEL_REVIEW_REQUIRED",
        "evidence/reasoning-analysis-report.json":
            "COMPLETE_WITH_MODEL_REVIEW_REQUIRED",
        "evidence/kural-generation-report.json":
            "COMPLETE_WITH_EDITORIAL_REVIEW_REQUIRED",
        "evidence/editorial-report.json":
            "COMPLETE_WITH_QA_REQUIRED",
    }

    import json

    for relative, status in historical_statuses.items():
        path = case_root / relative
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["status"] = status
        path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

    report = run_qa("LK-QA-TEST-HISTORY", case_root)

    for relative in historical_statuses:
        assert not any(
            relative in reason
            for reason in report["review_reasons"]
        )

def test_tamil_content_requires_review_when_human_gate_incomplete(tmp_path):
    create_case(tmp_path, review_required=False)

    kural_path = tmp_path / "output/09-kural/kural.md"
    kural_path.parent.mkdir(parents=True, exist_ok=True)
    kural_path.write_text(
        """# Test Kural

## Kural-Inspired Tamil

> **பெயரன்று பயன்பாடே பொருள்;**
> **உறைவோர்க்கு உறைவிடம் வீடு.**

## Review Gate

- [x] Manual legal coherence review completed
- [x] Legal fidelity review completed
- [ ] Tamil language review completed
- [ ] Founder approval recorded
""",
        encoding="utf-8",
    )

    report = run_qa("LK-TEST", tmp_path)

    assert report["verdict"] == "REVIEW_REQUIRED"
    assert (
        "Tamil editorial content requires independent review."
        in report["review_reasons"]
    )


def test_tamil_content_does_not_require_review_when_human_gate_complete(
    tmp_path,
):
    create_case(tmp_path, review_required=False)

    kural_path = tmp_path / "output/09-kural/kural.md"
    kural_path.parent.mkdir(parents=True, exist_ok=True)
    kural_path.write_text(
        """# Test Kural

## Kural-Inspired Tamil

> **பெயரன்று பயன்பாடே பொருள்;**
> **உறைவோர்க்கு உறைவிடம் வீடு.**

## Review Gate

- [x] Manual legal coherence review completed
- [x] Legal fidelity review completed
- [x] Tamil language review completed
- [x] Founder approval recorded
""",
        encoding="utf-8",
    )

    report = run_qa("LK-TEST", tmp_path)

    assert (
        "Tamil editorial content requires independent review."
        not in report["review_reasons"]
    )
