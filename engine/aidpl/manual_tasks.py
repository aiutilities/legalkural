from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


VALID_STATUSES = {
    "OPEN",
    "COMPLETE",
    "CANCELLED",
}

VALID_TASK_TYPES = {
    "LEGAL_FIDELITY_REVIEW",
    "TAMIL_LANGUAGE_REVIEW",
    "FOUNDER_APPROVAL",
    "KURAL_EDITORIAL_REVIEW",
    "EDITORIAL_REVIEW",
    "QA_REVIEW",
    "PUBLICATION_READINESS_REVIEW",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def task_store_path(case_root: Path) -> Path:
    return case_root.expanduser().resolve() / "manual-tasks.json"


def read_tasks(case_root: Path) -> list[dict[str, Any]]:
    path = task_store_path(case_root)

    if not path.exists():
        return []

    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, list):
        raise ValueError("Manual task store must contain a JSON array.")

    return payload


def write_tasks(
    case_root: Path,
    tasks: list[dict[str, Any]],
) -> None:
    path = task_store_path(case_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(tasks, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def create_task(
    *,
    case_root: Path,
    case_id: str,
    task_type: str,
    title: str,
    instructions: str,
    source_agent: str,
    blocking: bool = True,
) -> dict[str, Any]:
    if task_type not in VALID_TASK_TYPES:
        raise ValueError(f"Unsupported manual task type: {task_type}")

    if not case_id.strip():
        raise ValueError("case_id is required.")

    if not title.strip():
        raise ValueError("title is required.")

    if not instructions.strip():
        raise ValueError("instructions are required.")

    if not source_agent.strip():
        raise ValueError("source_agent is required.")

    tasks = read_tasks(case_root)

    task = {
        "task_id": f"MT-{uuid4().hex[:12].upper()}",
        "case_id": case_id,
        "task_type": task_type,
        "title": title,
        "instructions": instructions,
        "status": "OPEN",
        "source_agent": source_agent,
        "blocking": bool(blocking),
        "created_at_utc": utc_now(),
        "completed_at_utc": None,
        "completed_by": None,
        "completion_note": None,
    }

    tasks.append(task)
    write_tasks(case_root, tasks)

    return task


def get_task(
    case_root: Path,
    task_id: str,
) -> dict[str, Any]:
    for task in read_tasks(case_root):
        if task.get("task_id") == task_id:
            return task

    raise KeyError(f"Manual task not found: {task_id}")


def list_tasks(
    case_root: Path,
    *,
    status: str | None = None,
) -> list[dict[str, Any]]:
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(f"Unsupported manual task status: {status}")

    tasks = read_tasks(case_root)

    if status is None:
        return tasks

    return [
        task
        for task in tasks
        if task.get("status") == status
    ]


def complete_task(
    *,
    case_root: Path,
    task_id: str,
    completed_by: str,
    completion_note: str,
) -> dict[str, Any]:
    if not completed_by.strip():
        raise ValueError("completed_by is required.")

    if not completion_note.strip():
        raise ValueError("completion_note is required.")

    tasks = read_tasks(case_root)

    for task in tasks:
        if task.get("task_id") != task_id:
            continue

        if task.get("status") != "OPEN":
            raise ValueError(
                f"Manual task {task_id} is not OPEN."
            )

        task["status"] = "COMPLETE"
        task["completed_at_utc"] = utc_now()
        task["completed_by"] = completed_by
        task["completion_note"] = completion_note

        write_tasks(case_root, tasks)
        return task

    raise KeyError(f"Manual task not found: {task_id}")


def cancel_task(
    *,
    case_root: Path,
    task_id: str,
    completed_by: str,
    completion_note: str,
) -> dict[str, Any]:
    if not completed_by.strip():
        raise ValueError("completed_by is required.")

    if not completion_note.strip():
        raise ValueError("completion_note is required.")

    tasks = read_tasks(case_root)

    for task in tasks:
        if task.get("task_id") != task_id:
            continue

        if task.get("status") != "OPEN":
            raise ValueError(
                f"Manual task {task_id} is not OPEN."
            )

        task["status"] = "CANCELLED"
        task["completed_at_utc"] = utc_now()
        task["completed_by"] = completed_by
        task["completion_note"] = completion_note

        write_tasks(case_root, tasks)
        return task

    raise KeyError(f"Manual task not found: {task_id}")


def blocking_tasks_open(case_root: Path) -> bool:
    return any(
        task.get("status") == "OPEN"
        and task.get("blocking") is True
        for task in read_tasks(case_root)
    )
