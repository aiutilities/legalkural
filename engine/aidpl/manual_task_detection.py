from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import manual_tasks


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")

    return payload


def _task_key(
    case_id: str,
    task_type: str,
    source: str,
) -> str:
    return f"{case_id}:{task_type}:{source}"


def detect_required_tasks(
    case_id: str,
    case_root: Path,
) -> list[dict[str, Any]]:
    """
    Convert persisted review requirements into normalized manual-task
    specifications.

    Detection is read-only. It does not modify case artifacts or execute
    any worker.
    """

    case_root = case_root.expanduser().resolve()
    detected: list[dict[str, Any]] = []

    kural = read_json(
        case_root / "output/09-kural/kural-brief.json"
    )

    if kural and kural.get("requires_human_editorial_review") is True:
        detected.append(
            {
                "task_key": _task_key(
                    case_id,
                    "KURAL_EDITORIAL_REVIEW",
                    "output/09-kural/kural-brief.json",
                ),
                "case_id": case_id,
                "task_type": "KURAL_EDITORIAL_REVIEW",
                "title": "Review Legal Kural editorial draft",
                "description": (
                    "Complete human legal-fidelity and editorial review "
                    "of the Legal Kural draft before publication."
                ),
                "source": "output/09-kural/kural-brief.json",
                "blocking": True,
            }
        )

    editorial = read_json(
        case_root / "evidence/editorial-report.json"
    )

    if editorial:
        status = str(editorial.get("status") or "").upper()

        review_required = (
            editorial.get("human_review_required") is True
            or editorial.get("requires_human_review") is True
            or "REVIEW_REQUIRED" in status
        )

        if review_required:
            detected.append(
                {
                    "task_key": _task_key(
                        case_id,
                        "EDITORIAL_REVIEW",
                        "evidence/editorial-report.json",
                    ),
                    "case_id": case_id,
                    "task_type": "EDITORIAL_REVIEW",
                    "title": "Review editorial article",
                    "description": (
                        "Complete the required human editorial review "
                        "before the case may advance."
                    ),
                    "source": "evidence/editorial-report.json",
                    "blocking": True,
                }
            )

    qa = read_json(
        case_root / "evidence/validation-report.json"
    )

    if qa:
        verdict = str(qa.get("verdict") or "").upper()
        publication_ready = qa.get("publication_ready")

        if verdict == "REVIEW_REQUIRED":
            detected.append(
                {
                    "task_key": _task_key(
                        case_id,
                        "QA_REVIEW",
                        "evidence/validation-report.json",
                    ),
                    "case_id": case_id,
                    "task_type": "QA_REVIEW",
                    "title": "Resolve QA review requirement",
                    "description": (
                        "Review and resolve QA review items before "
                        "publication readiness may be established."
                    ),
                    "source": "evidence/validation-report.json",
                    "blocking": True,
                }
            )

        elif verdict == "PASS" and publication_ready is not True:
            detected.append(
                {
                    "task_key": _task_key(
                        case_id,
                        "PUBLICATION_READINESS_REVIEW",
                        "evidence/validation-report.json",
                    ),
                    "case_id": case_id,
                    "task_type": "PUBLICATION_READINESS_REVIEW",
                    "title": "Resolve publication readiness",
                    "description": (
                        "QA passed but publication readiness has not "
                        "been affirmatively established."
                    ),
                    "source": "evidence/validation-report.json",
                    "blocking": True,
                }
            )

    return detected


def _existing_task_key(task: dict[str, Any]) -> str | None:
    explicit = task.get("task_key")

    if isinstance(explicit, str) and explicit:
        return explicit

    case_id = task.get("case_id")
    task_type = task.get("task_type")
    source = task.get("source") or task.get("source_agent")

    if all(
        isinstance(value, str) and value
        for value in (case_id, task_type, source)
    ):
        return _task_key(case_id, task_type, source)

    return None


def create_detected_tasks(
    case_id: str,
    case_root: Path,
    task_store: Path,
) -> dict[str, Any]:
    """
    Persist detected tasks without duplicating an existing task having
    the same semantic task key.

    This function creates manual work only. It does not complete tasks,
    alter review artifacts, mutate orchestration plans, run providers,
    publish content, or execute LearningOS.
    """

    specifications = detect_required_tasks(
        case_id=case_id,
        case_root=case_root,
    )

    existing = manual_tasks.list_tasks(task_store)
    existing_keys = {
        key
        for task in existing
        if (key := _existing_task_key(task)) is not None
    }

    created: list[dict[str, Any]] = []
    skipped: list[str] = []

    for spec in specifications:
        key = spec["task_key"]

        if key in existing_keys:
            skipped.append(key)
            continue

        task = manual_tasks.create_task(
            case_root=task_store,
            case_id=spec["case_id"],
            task_type=spec["task_type"],
            title=spec["title"],
            instructions=spec["description"],
            source_agent=spec["source"],
            blocking=spec["blocking"],
        )

        created.append(task)
        existing_keys.add(key)

    return {
        "case_id": case_id,
        "detected": len(specifications),
        "created": len(created),
        "skipped_existing": len(skipped),
        "created_tasks": created,
        "skipped_task_keys": skipped,
    }
