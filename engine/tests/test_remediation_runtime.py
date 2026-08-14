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


def test_positive_core_consistency_is_not_actionable() -> None:
    assert not is_actionable_finding(
        "End-use/recipient-perspective test, statutory definitions, "
        "natural justice holding and batch-limitation are consistent "
        "across Facts, Issues, Reasoning, Decision and Article with "
        "page traceability. No contradiction detected on those cores."
    )


def test_correct_decision_limitation_is_not_actionable() -> None:
    assert not is_actionable_finding(
        "decision.json [REVIEW_REQUIRED]: Batch limitation and "
        "end-use qualification are consistently captured and correct."
    )


def test_optional_bench_completion_is_not_actionable() -> None:
    assert not is_actionable_finding(
        "metadata.json [REVIEW_REQUIRED]: Bench is null but article "
        "identifies Single Judge. Not a legal defect, but consider "
        "populating 'bench' if the source records it explicitly."
    )


def test_coherent_statutory_revalidation_is_not_actionable() -> None:
    assert not is_actionable_finding(
        "law.json [REVIEW_REQUIRED]: Section references for municipal "
        "definitions appear coherent with the reasoning; still advisable "
        "to re-validate against the quoted definitions."
    )


def test_article19_routes_to_law_despite_editorial_note_wording() -> None:
    classification, owner = route_finding(
        "Potential mis-citation of Constitution: References to "
        "Article 19(1)(8) appear in the Law artifact. This needs "
        "verification against the judgment and, if it is a typo, "
        "a clarifying editorial note."
    )

    assert classification == "LEGAL_FIDELITY_ERROR"
    assert owner == "LK-LAW"


def test_electricity_direction_routes_to_reason() -> None:
    classification, owner = route_finding(
        "Scope of operative direction to electricity tariff: "
        "verify from the judgment that this was a binding direction."
    )

    assert classification == "TRACEABILITY_GAP"
    assert owner == "LK-REASON"


def test_wp_year_mismatch_routes_to_extract() -> None:
    classification, owner = route_finding(
        "Metadata case numbering inconsistency: W.P.Nos.31337 and "
        "31342 show 2024 in advocates mapping but 2025 elsewhere; "
        "verify and harmonize."
    )

    assert classification == "LEGAL_FIDELITY_ERROR"
    assert owner == "LK-EXTRACT"


def test_source_confirmed_electricity_verification_is_not_remediation(
    tmp_path,
) -> None:
    case_root = tmp_path / "LK-TEST"
    working = case_root / "working"
    working.mkdir(parents=True)

    (working / "source-text.txt").write_text(
        (
            "The Court directs that electricity charges applicable to the "
            "petitioners shall be collected at the residential tariff."
        ),
        encoding="utf-8",
    )

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Scope of operative direction to electricity tariff: "
                "verify from the judgment that this was a binding direction."
            )
        ],
    }

    plan = build_remediation_plan(
        "LK-TEST",
        report,
        case_root=case_root,
    )

    assert plan["work_items"] == []
    assert plan["owners"] == []
    assert plan["earliest_owner"] is None


def test_source_anomaly_remains_actionable_even_when_text_is_in_source(
    tmp_path,
) -> None:
    case_root = tmp_path / "LK-TEST"
    working = case_root / "working"
    working.mkdir(parents=True)

    (working / "source-text.txt").write_text(
        (
            "The petitioners rely upon Article 19(1)(8) of the "
            "Constitution of India."
        ),
        encoding="utf-8",
    )

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Legal authority contains a likely error quoted verbatim "
                "from the judgment and requires verification."
            )
        ],
    }

    plan = build_remediation_plan(
        "LK-TEST",
        report,
        case_root=case_root,
    )

    assert len(plan["work_items"]) == 1
    assert plan["work_items"][0]["classification"] == "SOURCE_ANOMALY"
    assert plan["work_items"][0]["owner"] == "LK-LAW"
    assert plan["earliest_owner"] == "LK-LAW"


def test_electricity_verification_without_source_remains_fail_closed() -> None:
    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Scope of operative direction to electricity tariff: "
                "verify from the judgment that this was a binding direction."
            )
        ],
    }

    plan = build_remediation_plan("LK-TEST", report)

    assert len(plan["work_items"]) == 1
    assert plan["work_items"][0]["classification"] == "TRACEABILITY_GAP"
    assert plan["work_items"][0]["owner"] == "LK-REASON"
    assert plan["earliest_owner"] == "LK-REASON"


def test_source_confirmation_does_not_suppress_explicit_contradiction(
    tmp_path,
) -> None:
    case_root = tmp_path / "LK-TEST"
    working = case_root / "working"
    working.mkdir(parents=True)

    (working / "source-text.txt").write_text(
        (
            "Electricity charges shall be collected at the residential "
            "tariff."
        ),
        encoding="utf-8",
    )

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "There is an inconsistency in the electricity tariff "
                "direction and it requires verification."
            )
        ],
    }

    plan = build_remediation_plan(
        "LK-TEST",
        report,
        case_root=case_root,
    )

    assert len(plan["work_items"]) == 1


def test_remediation_runtime_builds_plan_with_case_root(
    tmp_path,
    monkeypatch,
) -> None:
    import aidpl.remediation_runtime as runtime

    case_root = tmp_path / "LK-TEST"
    evidence = case_root / "evidence"
    working = case_root / "working"

    evidence.mkdir(parents=True)
    working.mkdir(parents=True)

    (working / "source-text.txt").write_text(
        (
            "The Court directs that electricity charges shall be "
            "collected only at the residential tariff."
        ),
        encoding="utf-8",
    )

    qa_report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Scope of operative direction to electricity tariff: "
                "verify from the judgment that this was a binding direction."
            ),
            "Tamil couplet requires human language and cultural review.",
        ],
    }

    runtime.write_json(
        evidence / "qa-model-review-report.json",
        qa_report,
    )

    captured = {}
    original = runtime.build_remediation_plan

    def capturing_build_plan(
        case_id,
        report,
        case_root=None,
    ):
        captured["case_root"] = case_root
        return original(
            case_id,
            report,
            case_root=case_root,
        )

    monkeypatch.setattr(
        runtime,
        "build_remediation_plan",
        capturing_build_plan,
    )

    result = runtime.execute_remediation(
        root=tmp_path,
        case_id="LK-TEST",
        case_root=case_root,
        provider="mock",
        allow_live=False,
        max_iterations=1,
    )

    assert captured["case_root"] == case_root.resolve()

    iteration = result["iterations"][0]
    plan = iteration["plan"]

    # Electricity verification is source-confirmed and suppressed.
    assert plan["work_items"] == []

    # Human-only gate remains fail-closed.
    assert len(plan["human_review_items"]) == 1
    assert plan["earliest_owner"] is None
    assert plan["requires_human_review"] is True


def test_decompose_finding_splits_explicit_lettered_concerns() -> None:
    from aidpl.remediation_runtime import decompose_finding

    finding = (
        "article_markdown [REVIEW_REQUIRED]: Reflects accurately. However: "
        "(a) resolve the WP year inconsistency; "
        "(b) verify the electricity-tariff direction; "
        "(c) add a brief note if Article 19(1)(8) is a typographical slip."
    )

    parts = decompose_finding(finding)

    assert len(parts) == 3
    assert "WP year inconsistency" in parts[0]
    assert "electricity-tariff direction" in parts[1]
    assert "Article 19(1)(8)" in parts[2]


def test_decompose_finding_does_not_split_normal_prose() -> None:
    from aidpl.remediation_runtime import decompose_finding

    finding = (
        "Scope of operative direction to electricity tariff: verify from "
        "the judgment that this was a binding direction."
    )

    assert decompose_finding(finding) == [finding]


def test_compound_finding_source_confirms_only_electricity_clause(
    tmp_path,
) -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    case_root = tmp_path / "LK-TEST"
    working = case_root / "working"
    working.mkdir(parents=True)

    (working / "source-text.txt").write_text(
        (
            "The Court directs that electricity charges shall be collected "
            "at the residential tariff."
        ),
        encoding="utf-8",
    )

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "artifact_findings": [
            {
                "artifact": "article_markdown",
                "status": "REVIEW_REQUIRED",
                "findings": [
                    (
                        "Reflects the holdings accurately. However: "
                        "(a) resolve the WP year inconsistency and harmonize; "
                        "(b) verify the electricity-tariff direction as a "
                        "binding direction; "
                        "(c) verify Article 19(1)(8), which is not a valid "
                        "constitutional provision."
                    )
                ],
            }
        ],
    }

    plan = build_remediation_plan(
        "LK-TEST",
        report,
        case_root=case_root,
    )

    findings = [item["finding"] for item in plan["work_items"]]

    assert len(findings) == 2
    assert any("WP year inconsistency" in item for item in findings)
    assert any("Article 19(1)(8)" in item for item in findings)
    assert not any("electricity-tariff direction" in item for item in findings)

    assert plan["owners"] == ["LK-EXTRACT", "LK-LAW"]
    assert plan["earliest_owner"] == "LK-EXTRACT"


def test_compound_finding_without_source_keeps_all_concerns() -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Multiple concerns: "
                "(a) resolve the WP year inconsistency and harmonize; "
                "(b) verify the electricity tariff as a binding direction; "
                "(c) verify Article 19(1)(8), which is not a valid provision."
            )
        ],
    }

    plan = build_remediation_plan("LK-TEST", report)

    assert len(plan["work_items"]) == 3
    assert plan["owners"] == [
        "LK-EXTRACT",
        "LK-LAW",
        "LK-REASON",
    ]
    assert plan["earliest_owner"] == "LK-EXTRACT"



def test_duplicate_wp_year_findings_collapse_to_one_work_item() -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Inconsistency in WP years: W.P.Nos.31337 & 31342 "
                "show 2024 in advocates mapping but 2025 elsewhere."
            ),
        ],
        "artifact_findings": [
            {
                "artifact": "metadata",
                "status": "REVIEW_REQUIRED",
                "findings": [
                    (
                        "Advocates mapping lists W.P.Nos.31337 & 31342 "
                        "as 2024 while case numbers list them as 2025; "
                        "verify and harmonize."
                    ),
                ],
            },
            {
                "artifact": "article_markdown",
                "status": "REVIEW_REQUIRED",
                "findings": [
                    (
                        "Resolve the WP year inconsistency for "
                        "31337 and 31342: 2024 vs 2025."
                    ),
                ],
            },
        ],
    }

    plan = build_remediation_plan("LK-TEST", report)

    matches = [
        item
        for item in plan["work_items"]
        if (
            "31337" in item["finding"]
            or "31342" in item["finding"]
            or "wp year" in item["finding"].lower()
        )
    ]

    assert len(matches) == 1
    assert matches[0]["owner"] == "LK-EXTRACT"


def test_duplicate_article_19_findings_collapse_to_one_work_item() -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Potential mis-citation of Constitution: Article 19(1)(8) "
                "is not a valid sub-clause and requires verification."
            ),
        ],
        "artifact_findings": [
            {
                "artifact": "law",
                "status": "REVIEW_REQUIRED",
                "findings": [
                    (
                        "Article 19(1)(8) is not a valid provision; "
                        "verify the judgment text."
                    ),
                ],
            },
            {
                "artifact": "article_markdown",
                "status": "REVIEW_REQUIRED",
                "findings": [
                    (
                        "Add a brief note if Article 19(1)(8) is a "
                        "typographical slip."
                    ),
                ],
            },
        ],
    }

    plan = build_remediation_plan("LK-TEST", report)

    matches = [
        item
        for item in plan["work_items"]
        if "19(1)(8)" in item["finding"]
    ]

    assert len(matches) == 1
    assert matches[0]["owner"] == "LK-LAW"


def test_dedup_does_not_merge_distinct_legal_concerns() -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Article 19(1)(8) is not a valid constitutional "
                "provision and requires verification."
            ),
            (
                "Tamil Nadu Urban Local Bodies Act section citation "
                "appears incorrect and requires verification."
            ),
            (
                "WP year inconsistency for W.P.No.31337: "
                "2024 versus 2025; reconcile."
            ),
        ],
    }

    plan = build_remediation_plan("LK-TEST", report)

    assert len(plan["work_items"]) == 3

    owners = [item["owner"] for item in plan["work_items"]]
    assert owners.count("LK-LAW") == 2
    assert owners.count("LK-EXTRACT") == 1


def test_source_confirmed_electricity_stays_suppressed_after_dedup(
    tmp_path,
) -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    case_root = tmp_path / "LK-TEST"
    working = case_root / "working"
    working.mkdir(parents=True)

    (working / "source-text.txt").write_text(
        (
            "The Court directs that electricity charges shall be "
            "collected only at the residential tariff."
        ),
        encoding="utf-8",
    )

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Verify the electricity-tariff operative direction "
                "as a binding direction."
            ),
            (
                "Article 19(1)(8) is not a valid provision; verify."
            ),
        ],
    }

    plan = build_remediation_plan(
        "LK-TEST",
        report,
        case_root=case_root,
    )

    assert not any(
        "electricity" in item["finding"].lower()
        for item in plan["work_items"]
    )

    assert any(
        "19(1)(8)" in item["finding"]
        for item in plan["work_items"]
    )


def test_duplicate_human_findings_remain_human_only() -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            "Tamil couplet requires human language and cultural review.",
        ],
        "artifact_findings": [
            {
                "artifact": "kural",
                "status": "REVIEW_REQUIRED",
                "findings": [
                    (
                        "Tamil couplet requires human Tamil language "
                        "review before publication."
                    ),
                ],
            },
        ],
    }

    plan = build_remediation_plan("LK-TEST", report)

    assert plan["work_items"] == []
    assert plan["requires_human_review"] is True
    assert len(plan["human_review_items"]) >= 1

    assert all(
        item["owner"] is None
        and item["classification"] == "HUMAN_REVIEW_REQUIRED"
        for item in plan["human_review_items"]
    )


def test_remediation_ids_are_contiguous_after_deduplication() -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "WP year inconsistency for W.P.No.31337: "
                "2024 versus 2025; reconcile."
            ),
            (
                "Metadata case numbering inconsistency for 31337: "
                "2024 versus 2025; harmonize."
            ),
            (
                "Article 19(1)(8) is not a valid provision; verify."
            ),
            (
                "Article 19(1)(8) does not exist as a valid "
                "constitutional sub-clause; verification required."
            ),
            "Tamil couplet requires human language review.",
        ],
    }

    plan = build_remediation_plan("LK-TEST", report)

    all_items = (
        plan["work_items"]
        + plan["human_review_items"]
    )

    ids = [item["work_item_id"] for item in all_items]

    assert ids == [
        f"REM-{number:03d}"
        for number in range(1, len(ids) + 1)
    ]

    assert len(plan["work_items"]) == 2
    assert len(plan["human_review_items"]) == 1



def test_article19_dedup_uses_canonical_owner_regardless_of_order() -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "article_markdown [REVIEW_REQUIRED]: add a brief note "
                "if the Article 19(1)(8) reference in the judgment is "
                "a typographical slip. These are upstream fidelity "
                "clarifications, not rewrites of substance."
            ),
            (
                "Potential mis-citation of Constitution: Article 19(1)(8) "
                "is not a valid sub-clause and requires verification."
            ),
        ],
    }

    plan = build_remediation_plan("LK-TEST", report)

    matches = [
        item
        for item in plan["work_items"]
        if "19(1)(8)" in item["finding"]
    ]

    assert len(matches) == 1
    assert matches[0]["classification"] == "LEGAL_FIDELITY_ERROR"
    assert matches[0]["owner"] == "LK-LAW"
    assert plan["owners"] == ["LK-LAW"]
    assert plan["earliest_owner"] == "LK-LAW"



def test_wp_year_concern_becomes_source_anomaly_when_source_contains_both_years(
    tmp_path,
) -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    case_root = tmp_path / "LK-TEST"
    working = case_root / "working"
    working.mkdir(parents=True)

    (working / "source-text.txt").write_text(
        (
            "W.P.No.31337 of 2024 appears in one portion of the judgment. "
            "W.P.No.31337 of 2025 appears in another portion."
        ),
        encoding="utf-8",
    )

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Inconsistency in WP years: W.P.No.31337 appears as "
                "2024 and 2025. Verify and reconcile."
            )
        ],
    }

    plan = build_remediation_plan(
        "LK-TEST",
        report,
        case_root=case_root,
    )

    assert len(plan["work_items"]) == 1

    item = plan["work_items"][0]

    assert item["classification"] == "SOURCE_ANOMALY"
    assert item["owner"] == "LK-EXTRACT"
    assert plan["owners"] == ["LK-EXTRACT"]
    assert plan["earliest_owner"] == "LK-EXTRACT"


def test_wp_year_concern_stays_fidelity_error_without_source_conflict(
    tmp_path,
) -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    case_root = tmp_path / "LK-TEST"
    working = case_root / "working"
    working.mkdir(parents=True)

    (working / "source-text.txt").write_text(
        "W.P.No.31337 of 2025.",
        encoding="utf-8",
    )

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Inconsistency in WP years: metadata lists "
                "W.P.No.31337 as 2024 while the article lists 2025."
            )
        ],
    }

    plan = build_remediation_plan(
        "LK-TEST",
        report,
        case_root=case_root,
    )

    assert len(plan["work_items"]) == 1

    item = plan["work_items"][0]

    assert item["classification"] == "LEGAL_FIDELITY_ERROR"
    assert item["owner"] == "LK-EXTRACT"


def test_article_19_1_8_becomes_source_anomaly_when_present_in_source(
    tmp_path,
) -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    case_root = tmp_path / "LK-TEST"
    working = case_root / "working"
    working.mkdir(parents=True)

    (working / "source-text.txt").write_text(
        (
            "The judgment records the contention under "
            "Article 19(1)(8) of the Constitution."
        ),
        encoding="utf-8",
    )

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Article 19(1)(8) is not a valid constitutional "
                "provision and requires verification."
            )
        ],
    }

    plan = build_remediation_plan(
        "LK-TEST",
        report,
        case_root=case_root,
    )

    assert len(plan["work_items"]) == 1

    item = plan["work_items"][0]

    assert item["classification"] == "SOURCE_ANOMALY"
    assert item["owner"] == "LK-LAW"
    assert plan["owners"] == ["LK-LAW"]
    assert plan["earliest_owner"] == "LK-LAW"


def test_article_19_1_8_stays_fidelity_error_when_absent_from_source(
    tmp_path,
) -> None:
    from aidpl.remediation_runtime import build_remediation_plan

    case_root = tmp_path / "LK-TEST"
    working = case_root / "working"
    working.mkdir(parents=True)

    (working / "source-text.txt").write_text(
        (
            "The judgment discusses Article 19(1)(g) "
            "of the Constitution."
        ),
        encoding="utf-8",
    )

    report = {
        "verdict": "REVIEW_REQUIRED",
        "confidence": 0.8,
        "review_findings": [
            (
                "Article 19(1)(8) is not a valid constitutional "
                "provision and requires verification."
            )
        ],
    }

    plan = build_remediation_plan(
        "LK-TEST",
        report,
        case_root=case_root,
    )

    assert len(plan["work_items"]) == 1

    item = plan["work_items"][0]

    assert item["classification"] == "LEGAL_FIDELITY_ERROR"
    assert item["owner"] == "LK-LAW"
