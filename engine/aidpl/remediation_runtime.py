from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGE_ORDER = [
    "LK-EXTRACT",
    "LK-LAW",
    "LK-REASON",
    "LK-KURAL",
    "LK-EDITOR",
    "LK-QA",
]

KEYWORDS = {
    "LK-EXTRACT": [
        "metadata", "timeline", "fact", "evidence", "party",
        "date", "source page", "traceability",
    ],
    "LK-LAW": [
        "statute", "section", "regulation", "notification",
        "precedent", "doctrine", "authority",
        "article 14", "article 19", "article 226",
    ],
    "LK-REASON": [
        "reasoning", "ratio", "obiter", "holding", "finding",
        "decision", "relief", "direction", "outcome", "limitation",
    ],
    "LK-KURAL": [
        "kural", "tamil", "thirukkural",
        "universal principle", "compressed title", "moral",
    ],
    "LK-EDITOR": [
        "article", "editorial", "heading", "disclaimer",
        "plain language", "word count", "publication status", "story",
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def flatten_findings(report: dict[str, Any]) -> list[str]:
    findings: list[str] = []

    for key in ["blocking_errors", "review_findings"]:
        for item in report.get(key, []):
            if isinstance(item, str):
                findings.append(item)

    for artifact in report.get("artifact_findings", []):
        if not isinstance(artifact, dict):
            continue

        name = str(artifact.get("artifact") or "artifact")
        status = str(artifact.get("status") or "").upper()

        # PASS is evidence, not remediation work.
        if status == "PASS":
            continue

        for item in artifact.get("findings", []):
            if isinstance(item, str):
                findings.append(f"{name} [{status}]: {item}")

    return findings


SOURCE_ANOMALY_RULES = [
    (
        "LK-EXTRACT",
        [
            "source artifact",
            "source data",
            "source record",
            "metadata",
            "timeline",
            "material fact",
            "verified fact",
            "evidence item",
            "source page",
            "traceability",
        ],
    ),
    (
        "LK-LAW",
        [
            "legal authority",
            "legal framework",
            "statute",
            "precedent",
            "case law",
            "section",
            "regulation",
            "notification",
        ],
    ),
    (
        "LK-REASON",
        [
            "reasoning artifact",
            "reasoning step",
            "ratio",
            "holding",
            "finding",
            "decision artifact",
            "operative direction",
            "relief",
            "outcome",
        ],
    ),
    (
        "LK-KURAL",
        [
            "kural brief",
            "tamil kural",
            "thirukkural",
        ],
    ),
]


FINDING_CLASSIFICATIONS = {
    "LEGAL_FIDELITY_ERROR",
    "SOURCE_ANOMALY",
    "EDITORIAL",
    "TRACEABILITY_GAP",
    "HUMAN_REVIEW_REQUIRED",
}


def classify_finding(finding: str) -> str:
    """Classify a QA finding for remediation routing."""
    lowered = finding.lower()

    human_markers = (
        "human review",
        "human language",
        "human tamil",
        "cultural review",
        "requires human",
        "tamil couplet",
    )
    if any(marker in lowered for marker in human_markers):
        return "HUMAN_REVIEW_REQUIRED"

    traceability_markers = (
        "traceability",
        "source-page mapping",
        "source page mapping",
        "page-level",
        "page level",
        "source hook",
    )
    if any(marker in lowered for marker in traceability_markers):
        return "TRACEABILITY_GAP"

    source_anomaly_markers = (
        "quoted verbatim",
        "as recorded in the judgment",
        "source inconsistency",
        "source anomaly",
        "source typo",
        "likely error",
        "likely incorrect",
    )
    if any(marker in lowered for marker in source_anomaly_markers):
        return "SOURCE_ANOMALY"

    editorial_markers = (
        "article.md",
        "article markdown",
        "article heading",
        "article section",
        "article contains",
        "article ends",
        "editorial",
        "heading",
        "placeholder",
        "readability",
        "wording",
        "disclaimer",
        "publication status",
    )
    if any(marker in lowered for marker in editorial_markers):
        return "EDITORIAL"

    return "LEGAL_FIDELITY_ERROR"


def source_anomaly_owner(finding: str) -> str | None:
    """Return the earliest upstream owner explicitly implicated by a finding."""
    lowered = finding.lower()

    anomaly_markers = [
        "missing",
        "placeholder",
        "incomplete",
        "unsupported",
        "contradict",
        "conflict",
        "absent",
        "not established",
        "not supported",
        "cannot be verified",
        "requires verification",
    ]

    if not any(marker in lowered for marker in anomaly_markers):
        return None

    for stage, markers in SOURCE_ANOMALY_RULES:
        if any(marker in lowered for marker in markers):
            return stage

    return None


def owner_for_finding(finding: str) -> str:
    source_owner = source_anomaly_owner(finding)
    if source_owner is not None:
        return source_owner

    lowered = finding.lower()
    scores = {
        stage: sum(
            1 for keyword in keywords
            if keyword in lowered
        )
        for stage, keywords in KEYWORDS.items()
    }

    best_stage = max(scores, key=scores.get)
    return best_stage if scores[best_stage] else "LK-EDITOR"



AFFIRMATIVE_FINDING_MARKERS = (
    "internally consistent",
    "faithfully reflects",
    "fairly characterized",
    "fairly characterised",
    "coherently carried",
    "correctly flagged",
    "correctly identifies",
    "correctly states",
    "is traceable",
    "are traceable",
    "no legal advice offered",
)


def is_actionable_finding(finding: str) -> bool:
    """Return True only when a QA observation requires actual remediation."""
    lowered = finding.lower()

    # Explicit affirmative/negated observations are evidence, not work.
    non_actionable_phrases = (
        "no contradiction detected",
        "no contradiction",
        "no distortion detected",
        "no invented facts detected",
        "consistently captured and correct",
        "substantive content appears coherent",
        "not a legal defect",
        "not a substantive defect",
    )

    if any(phrase in lowered for phrase in non_actionable_phrases):
        return False

    affirmative_markers = AFFIRMATIVE_FINDING_MARKERS + (
        "appears coherent",
        "acceptable",
    )

    strong_defect_markers = (
        "inconsistency",
        "incorrect",
        "unsupported",
        "missing required",
        "does not exist",
        "not supported",
        "must be corrected",
        "requires correction",
        "mis-citation",
        "mis-cited",
    )

    if any(marker in lowered for marker in affirmative_markers):
        if not any(marker in lowered for marker in strong_defect_markers):
            return False

    optional_markers = (
        "consider populating",
        "consider adding",
        "advisable to",
        "may consider",
        "could consider",
        "for completeness",
    )

    if any(marker in lowered for marker in optional_markers):
        if not any(marker in lowered for marker in strong_defect_markers):
            return False

    return True

def route_finding(finding: str) -> tuple[str, str | None]:
    """Classify a finding and choose its earliest true remediation owner."""
    classification = classify_finding(finding)

    if classification == "HUMAN_REVIEW_REQUIRED":
        return classification, None

    lowered = finding.lower()

    # A source anomaly means the questionable text originates in the
    # authoritative source itself. Preserve that classification while
    # still routing it to the earliest upstream stage able to verify it.
    if classification == "SOURCE_ANOMALY":
        owner = source_anomaly_owner(finding)
        if owner is None:
            owner = owner_for_finding(finding)
        return classification, owner

    # Domain ownership outranks incidental wording such as
    # "editorial note" when the actual defect is upstream.
    legal_domain_markers = (
        "article 19",
        "constitutional citation",
        "statute",
        "section ",
        "regulation",
        "legal authority",
        "law artifact",
        "law.json",
        "precedent",
    )
    legal_problem_markers = (
        "incorrect",
        "mis-citation",
        "mis-cited",
        "not a valid",
        "does not exist",
        "verify",
        "verification",
        "questionable",
    )

    if (
        any(marker in lowered for marker in legal_domain_markers)
        and any(marker in lowered for marker in legal_problem_markers)
    ):
        return "LEGAL_FIDELITY_ERROR", "LK-LAW"

    reason_domain_markers = (
        "decision",
        "operative direction",
        "relief",
        "electricity tariff",
        "binding direction",
    )
    reason_problem_markers = (
        "verify",
        "verification",
        "unsupported",
        "over-breadth",
        "overbreadth",
        "not clearly supported",
    )

    if (
        any(marker in lowered for marker in reason_domain_markers)
        and any(marker in lowered for marker in reason_problem_markers)
    ):
        return "TRACEABILITY_GAP", "LK-REASON"

    extract_domain_markers = (
        "metadata",
        "case number",
        "case numbering",
        "wp year",
        "w.p.no",
        "advocates mapping",
    )
    extract_problem_markers = (
        "inconsistency",
        "mismatch",
        "conflict",
        "reconcile",
        "harmonize",
        "harmonise",
        "verify",
    )

    if (
        any(marker in lowered for marker in extract_domain_markers)
        and any(marker in lowered for marker in extract_problem_markers)
    ):
        return "LEGAL_FIDELITY_ERROR", "LK-EXTRACT"

    upstream_defect_markers = (
        "missing",
        "incomplete",
        "contradictory",
        "unsupported",
        "unverified",
        "not verified",
        "lacks",
        "lack of",
    )

    upstream_artifact_markers = (
        "fact",
        "issue",
        "evidence",
        "source",
        "authority",
        "law",
        "reasoning",
        "decision",
        "operative direction",
        "relief",
        "outcome",
    )

    has_upstream_defect = any(
        marker in lowered for marker in upstream_defect_markers
    )
    has_upstream_artifact = any(
        marker in lowered for marker in upstream_artifact_markers
    )

    # An editorial symptom must not hide an explicitly stated upstream cause.
    if has_upstream_defect and has_upstream_artifact:
        owner = owner_for_finding(finding)
        if owner != "LK-EDITOR":
            return "LEGAL_FIDELITY_ERROR", owner

    if classification == "EDITORIAL":
        return classification, "LK-EDITOR"

    return classification, owner_for_finding(finding)


def source_text_for_case(case_root: Path | None) -> str:
    """Load authoritative source text when a case root is available."""
    if case_root is None:
        return ""

    source_path = case_root / "working/source-text.txt"
    if not source_path.exists():
        return ""

    return source_path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def source_confirms_finding(
    finding: str,
    source_text: str,
) -> bool:
    """Return True only for narrow propositions expressly confirmed by source.

    This is intentionally conservative. It suppresses a verification-only
    remediation item only when the authoritative judgment text itself
    expressly establishes the proposition being questioned.

    Contradictions, source anomalies, legal miscitation concerns and other
    substantive defects remain actionable.
    """
    if not source_text:
        return False

    def normalize_match_text(value: str) -> str:
        """Normalize superficial punctuation differences for evidence matching."""
        return " ".join(
            value.lower()
            .replace("-", " ")
            .replace("–", " ")
            .replace("—", " ")
            .split()
        )

    lowered = normalize_match_text(finding)
    source = normalize_match_text(source_text)

    # Never suppress a finding already identified as a source anomaly.
    if classify_finding(finding) == "SOURCE_ANOMALY":
        return False

    # Never suppress explicit contradiction/fidelity defects merely because
    # one version of the disputed text occurs somewhere in the source.
    defect_markers = (
        "inconsistency",
        "mismatch",
        "conflict",
        "contradiction",
        "incorrect",
        "mis-citation",
        "mis-cited",
        "does not exist",
        "not a valid",
    )
    if any(marker in lowered for marker in defect_markers):
        return False

    # Narrow source-confirmation contract for an operative electricity-tariff
    # verification request. Both concepts must occur in the authoritative
    # source; this does not infer party status or cure unrelated defects.
    electricity_markers = (
        "electricity tariff",
        "electricity charges",
    )
    direction_markers = (
        "residential tariff",
        "residential rate",
    )

    finding_is_electricity_verification = (
        any(marker in lowered for marker in electricity_markers)
        and any(
            marker in lowered
            for marker in (
                "verify",
                "verification",
                "binding direction",
                "operative direction",
            )
        )
    )

    source_has_electricity_direction = (
        any(marker in source for marker in electricity_markers)
        and any(marker in source for marker in direction_markers)
    )

    if (
        finding_is_electricity_verification
        and source_has_electricity_direction
    ):
        return True

    return False


def decompose_finding(finding: str) -> list[str]:
    """Split only explicitly enumerated compound QA findings.

    QA sometimes returns one finding containing independent ``(a)``, ``(b)``,
    ``(c)`` remediation concerns.  Those concerns must be evaluated
    independently so source confirmation of one clause cannot suppress, or be
    blocked by, an unrelated clause.

    This intentionally does not perform general sentence splitting.
    """
    import re

    matches = list(
        re.finditer(
            r"(?<!\w)\(([a-z])\)\s+",
            finding,
            flags=re.IGNORECASE,
        )
    )

    if len(matches) < 2:
        return [finding]

    prefix = finding[:matches[0].start()].strip()
    parts: list[str] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(finding)
        )

        clause = finding[start:end].strip()
        clause = clause.strip(" ;")

        if not clause:
            continue

        if prefix:
            parts.append(f"{prefix} {clause}")
        else:
            parts.append(clause)

    return parts or [finding]


def build_remediation_plan(
    case_id: str,
    qa_report: dict[str, Any],
    case_root: Path | None = None,
) -> dict[str, Any]:
    findings = [
        concern
        for finding in flatten_findings(qa_report)
        for concern in decompose_finding(finding)
    ]
    source_text = source_text_for_case(case_root)
    work_items: list[dict[str, Any]] = []

    human_review_items: list[dict[str, Any]] = []

    item_number = 0

    for finding in findings:
        if not is_actionable_finding(finding):
            continue

        if source_confirms_finding(finding, source_text):
            continue

        classification, owner = route_finding(finding)
        item_number += 1

        item = {
            "work_item_id": f"REM-{item_number:03d}",
            "owner": owner,
            "classification": classification,
            "finding": finding,
            "status": "PENDING",
        }

        if classification == "HUMAN_REVIEW_REQUIRED":
            human_review_items.append(item)
        else:
            work_items.append(item)

    owners = sorted(
        {item["owner"] for item in work_items},
        key=STAGE_ORDER.index,
    )

    return {
        "schema_version": "1.0",
        "agent_id": "LK-REMEDIATION",
        "case_id": case_id,
        "status": "PLANNED",
        "created_at_utc": utc_now(),
        "qa_verdict": qa_report.get("verdict"),
        "qa_confidence": qa_report.get("confidence"),
        "earliest_owner": owners[0] if owners else None,
        "owners": owners,
        "work_items": work_items,
        "human_review_items": human_review_items,
        "requires_human_review": bool(human_review_items),
        "publication_ready": False,
    }


def command(
    root: Path,
    executable: str,
    case_id: str,
    case_root: Path,
    provider: str | None = None,
    allow_live: bool = False,
) -> list[str]:
    result = [
        str(root / "bin" / executable),
        "--case-id",
        case_id,
        "--case-root",
        str(case_root),
    ]

    if provider:
        result.extend(["--provider", provider])

    if allow_live:
        result.append("--allow-live")

    return result


def run_command(root: Path, args: list[str]) -> None:
    subprocess.run(args, cwd=root, check=True)


def stages_from(owner: str) -> list[str]:
    return STAGE_ORDER[STAGE_ORDER.index(owner):]


def execute_remediation(
    root: Path,
    case_id: str,
    case_root: Path,
    provider: str,
    allow_live: bool,
    max_iterations: int,
) -> dict[str, Any]:
    case_root = case_root.expanduser().resolve()
    qa_path = case_root / "evidence/qa-model-review-report.json"
    iterations: list[dict[str, Any]] = []

    for iteration in range(1, max_iterations + 1):
        qa_report = read_json(qa_path)

        if qa_report.get("verdict") == "PASS":
            break

        plan = build_remediation_plan(
            case_id,
            qa_report,
            case_root=case_root,
        )
        plan["iteration"] = iteration

        write_json(
            case_root / f"evidence/remediation-plan-{iteration:03d}.json",
            plan,
        )

        execution: list[dict[str, Any]] = []

        # Human-only findings must remain fail-closed.
        # Do not invent an autonomous owner or execute downstream workers.
        if plan["earliest_owner"] is None:
            iteration_report = {
                "iteration": iteration,
                "plan": plan,
                "execution": execution,
                "qa_verdict_after_iteration": qa_report.get("verdict"),
                "qa_confidence_after_iteration": qa_report.get("confidence"),
                "completed_at_utc": utc_now(),
            }

            iterations.append(iteration_report)

            write_json(
                case_root
                / f"evidence/remediation-iteration-{iteration:03d}.json",
                iteration_report,
            )
            break

        for stage in stages_from(plan["earliest_owner"]):
            started = utc_now()

            if stage == "LK-EXTRACT":
                steps = [
                    command(root, "aidpl-review-extract", case_id, case_root, provider, allow_live),
                    command(root, "aidpl-review-run", case_id, case_root),
                ]
            elif stage == "LK-LAW":
                steps = [
                    command(root, "aidpl-review-law", case_id, case_root, provider, allow_live),
                    command(root, "aidpl-review-after-law", case_id, case_root),
                ]
            elif stage == "LK-REASON":
                steps = [
                    command(root, "aidpl-review-reason", case_id, case_root, provider, allow_live),
                    command(root, "aidpl-review-after-reason", case_id, case_root),
                ]
            elif stage == "LK-KURAL":
                steps = [
                    command(root, "aidpl-review-kural", case_id, case_root, provider, allow_live),
                    command(root, "aidpl-review-after-kural", case_id, case_root),
                ]
            elif stage == "LK-EDITOR":
                steps = [
                    command(root, "aidpl-review-editor", case_id, case_root, provider, allow_live),
                    command(root, "aidpl-review-after-editor", case_id, case_root),
                ]
            else:
                steps = [
                    command(root, "aidpl-review-qa", case_id, case_root, provider, allow_live),
                ]

            try:
                for step in steps:
                    run_command(root, step)
                status = "COMPLETE"
                error = None
            except subprocess.CalledProcessError as exc:
                status = "FAILED"
                error = (
                    f"Command failed with exit status "
                    f"{exc.returncode}: {' '.join(exc.cmd)}"
                )

            execution.append(
                {
                    "stage": stage,
                    "status": status,
                    "started_at_utc": started,
                    "completed_at_utc": utc_now(),
                    "error": error,
                }
            )

            if status == "FAILED":
                break

        latest_qa = read_json(qa_path)

        iteration_report = {
            "iteration": iteration,
            "plan": plan,
            "execution": execution,
            "qa_verdict_after_iteration": latest_qa.get("verdict"),
            "qa_confidence_after_iteration": latest_qa.get("confidence"),
            "completed_at_utc": utc_now(),
        }
        iterations.append(iteration_report)

        write_json(
            case_root / f"evidence/remediation-iteration-{iteration:03d}.json",
            iteration_report,
        )

        if any(step["status"] == "FAILED" for step in execution):
            break

        if latest_qa.get("verdict") == "PASS":
            break

    final_qa = read_json(qa_path)

    report = {
        "schema_version": "1.0",
        "runtime": "AIDPL Autonomous Remediation Runtime",
        "runtime_version": "0.1.0",
        "case_id": case_id,
        "status": (
            "PASS"
            if final_qa.get("verdict") == "PASS"
            else "STOPPED_WITH_REVIEW_REQUIRED"
        ),
        "completed_at_utc": utc_now(),
        "iterations": iterations,
        "final_qa_verdict": final_qa.get("verdict"),
        "final_qa_confidence": final_qa.get("confidence"),
        "founder_gate": (
            "OPEN"
            if final_qa.get("verdict") == "PASS"
            else "BLOCKED"
        ),
        "publication_ready": False,
        "next_action": (
            "FOUNDER_REVIEW"
            if final_qa.get("verdict") == "PASS"
            else "HUMAN_EXCEPTION_REVIEW"
        ),
    }

    write_json(
        case_root / "evidence/remediation-runtime-report.json",
        report,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-remediate",
        description="Plan and execute autonomous Legal Kural remediation.",
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai", "deepseek", "qwen"],
    )
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--max-iterations", type=int, default=1)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(__file__).resolve().parents[2]

    if args.provider != "mock" and not args.allow_live:
        print("ERROR: Live remediation requires --allow-live.", file=sys.stderr)
        return 1

    if args.max_iterations < 1 or args.max_iterations > 3:
        print(
            "ERROR: --max-iterations must be between 1 and 3.",
            file=sys.stderr,
        )
        return 1

    try:
        report = execute_remediation(
            root=root,
            case_id=args.case_id,
            case_root=args.case_root,
            provider=args.provider,
            allow_live=args.allow_live,
            max_iterations=args.max_iterations,
        )
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print()
    print("=" * 76)
    print("LEGAL KURAL AUTONOMOUS REMEDIATION")
    print("=" * 76)
    print(f"Case        : {args.case_id}")
    print(f"Iterations  : {len(report['iterations'])}")
    print(f"Final QA    : {report['final_qa_verdict']}")
    print(f"Confidence  : {report['final_qa_confidence']}")
    print(f"Founder Gate: {report['founder_gate']}")
    print(f"Next Action : {report['next_action']}")
    print("=" * 76)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
