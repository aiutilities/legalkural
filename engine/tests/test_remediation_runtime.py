from aidpl.remediation_runtime import (
    build_remediation_plan,
    flatten_findings,
    owner_for_finding,
    stages_from,
)


def test_flatten_findings() -> None:
    report = {
        "blocking_errors": ["Missing metadata"],
        "review_findings": ["Article heading mismatch"],
        "artifact_findings": [
            {
                "artifact": "law.json",
                "status": "REVIEW_REQUIRED",
                "findings": ["Incorrect precedent treatment"],
            }
        ],
    }

    findings = flatten_findings(report)

    assert len(findings) == 3
    assert "law.json" in findings[2]


def test_owner_mapping() -> None:
    assert owner_for_finding(
        "Timeline date conflicts with source page."
    ) == "LK-EXTRACT"

    assert owner_for_finding(
        "Precedent treatment is unsupported."
    ) == "LK-LAW"

    assert owner_for_finding(
        "Ratio candidate distorts the holding."
    ) == "LK-REASON"

    assert owner_for_finding(
        "Tamil Kural requires correction."
    ) == "LK-KURAL"

    assert owner_for_finding(
        "Article disclaimer is incomplete."
    ) == "LK-EDITOR"


def test_build_plan_uses_earliest_owner() -> None:
    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.7,
        "review_findings": [
            "Article disclaimer is incomplete.",
            "Timeline date conflicts with source page.",
        ],
    }

    plan = build_remediation_plan("LK-TEST", report)

    assert plan["earliest_owner"] == "LK-EXTRACT"
    assert "LK-EDITOR" in plan["owners"]


def test_stages_from_reason() -> None:
    assert stages_from("LK-REASON") == [
        "LK-REASON",
        "LK-KURAL",
        "LK-EDITOR",
        "LK-QA",
    ]
