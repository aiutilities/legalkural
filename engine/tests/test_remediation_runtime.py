from aidpl.remediation_runtime import (
    build_remediation_plan,
    classify_finding,
    flatten_findings,
    is_actionable_finding,
    owner_for_finding,
    route_finding,
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


def test_source_anomaly_routes_reasoning_placeholder_upstream() -> None:
    finding = (
        "Article contains a placeholder because the reasoning artifact "
        "is missing a verified reasoning step."
    )

    assert owner_for_finding(finding) == "LK-REASON"


def test_source_anomaly_routes_missing_fact_to_extract() -> None:
    finding = (
        "Article cannot resolve the issue because a verified fact is "
        "missing from the source artifacts."
    )

    assert owner_for_finding(finding) == "LK-EXTRACT"


def test_source_anomaly_routes_missing_authority_to_law() -> None:
    finding = (
        "The article statement is unsupported because the legal authority "
        "is missing from the legal framework."
    )

    assert owner_for_finding(finding) == "LK-LAW"


def test_pure_editorial_defect_remains_editor_owned() -> None:
    assert owner_for_finding(
        "Article heading and plain language need editorial correction."
    ) == "LK-EDITOR"


def test_build_plan_uses_upstream_source_for_article_placeholder() -> None:
    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Article contains a placeholder because the reasoning "
                "artifact is missing a verified reasoning step."
            )
        ],
    }

    plan = build_remediation_plan("LK-TEST", report)

    assert plan["earliest_owner"] == "LK-REASON"
    assert plan["owners"] == ["LK-REASON"]


def test_pass_artifact_findings_are_not_remediation_work() -> None:
    report = {
        "artifact_findings": [
            {
                "artifact": "metadata",
                "status": "PASS",
                "findings": ["Core metadata is correct."],
            },
            {
                "artifact": "law",
                "status": "REVIEW_REQUIRED",
                "findings": ["Precedent treatment is unsupported."],
            },
        ],
    }

    findings = flatten_findings(report)

    assert len(findings) == 1
    assert "law [REVIEW_REQUIRED]" in findings[0]
    assert "metadata" not in findings[0]


def test_human_review_classification() -> None:
    assert classify_finding(
        "Tamil couplet requires human language and cultural review."
    ) == "HUMAN_REVIEW_REQUIRED"


def test_source_anomaly_classification() -> None:
    assert classify_finding(
        "Article 19(1)(8) is a likely error quoted verbatim from the judgment."
    ) == "SOURCE_ANOMALY"


def test_traceability_gap_classification() -> None:
    assert classify_finding(
        "Reasoning lacks page-level traceability."
    ) == "TRACEABILITY_GAP"


def test_editorial_classification() -> None:
    assert classify_finding(
        "Article heading needs editorial correction."
    ) == "EDITORIAL"


def test_human_only_plan_has_no_autonomous_owner() -> None:
    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            "Tamil couplet requires human language and cultural review."
        ],
    }

    plan = build_remediation_plan("LK-TEST", report)

    assert plan["earliest_owner"] is None
    assert plan["owners"] == []
    assert plan["work_items"] == []
    assert len(plan["human_review_items"]) == 1
    assert plan["requires_human_review"] is True


def test_mixed_plan_separates_human_and_autonomous_items() -> None:
    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            "Tamil couplet requires human language and cultural review.",
            "Article heading needs editorial correction.",
        ],
    }

    plan = build_remediation_plan("LK-TEST", report)

    assert plan["earliest_owner"] == "LK-EDITOR"
    assert len(plan["work_items"]) == 1
    assert len(plan["human_review_items"]) == 1


def test_constitutional_article_is_not_editorial() -> None:
    classification = classify_finding(
        "Constitutional citation appears incorrect: "
        "Article 19(1)(8) does not exist."
    )

    assert classification != "EDITORIAL"


def test_affirmative_ratio_observation_is_not_actionable() -> None:
    assert not is_actionable_finding(
        "Core ratio, facts, issues, reasoning, and disposition "
        "are internally consistent and traceable across artifacts."
    )


def test_affirmative_kural_observation_is_not_actionable() -> None:
    assert not is_actionable_finding(
        "Kural substance faithfully reflects the holding and limits; "
        "no legal advice offered."
    )


def test_editorial_placeholder_routes_to_editor() -> None:
    classification, owner = route_finding(
        "article.md contains redundant placeholder sections "
        "that require editorial cleanup."
    )

    assert classification == "EDITORIAL"
    assert owner == "LK-EDITOR"


def test_human_tamil_route_has_no_autonomous_owner() -> None:
    classification, owner = route_finding(
        "Tamil couplet requires human language and cultural review."
    )

    assert classification == "HUMAN_REVIEW_REQUIRED"
    assert owner is None


def test_source_anomaly_uses_upstream_owner_when_known() -> None:
    classification, owner = route_finding(
        "Legal authority contains a likely error quoted verbatim "
        "from the judgment and requires verification."
    )

    assert classification == "SOURCE_ANOMALY"
    assert owner == "LK-LAW"
