from pathlib import Path

import pytest

from aidpl.manual_tasks import (
    blocking_tasks_open,
    cancel_task,
    complete_task,
    create_task,
    get_task,
    list_tasks,
    read_tasks,
)


def test_empty_store(tmp_path: Path) -> None:
    assert read_tasks(tmp_path) == []
    assert blocking_tasks_open(tmp_path) is False


def test_create_manual_task(tmp_path: Path) -> None:
    task = create_task(
        case_root=tmp_path,
        case_id="LK-TEST-001",
        task_type="LEGAL_FIDELITY_REVIEW",
        title="Review legal fidelity",
        instructions="Verify article against judgment.",
        source_agent="LK-QA",
    )

    assert task["task_id"].startswith("MT-")
    assert task["status"] == "OPEN"
    assert task["blocking"] is True
    assert task["completed_at_utc"] is None

    stored = read_tasks(tmp_path)

    assert len(stored) == 1
    assert stored[0]["task_id"] == task["task_id"]
    assert blocking_tasks_open(tmp_path) is True


def test_get_and_list_tasks(tmp_path: Path) -> None:
    first = create_task(
        case_root=tmp_path,
        case_id="LK-TEST-001",
        task_type="LEGAL_FIDELITY_REVIEW",
        title="Legal review",
        instructions="Review legal fidelity.",
        source_agent="LK-QA",
    )

    create_task(
        case_root=tmp_path,
        case_id="LK-TEST-001",
        task_type="TAMIL_LANGUAGE_REVIEW",
        title="Tamil review",
        instructions="Review Tamil editorial writing.",
        source_agent="LK-KURAL",
    )

    assert get_task(tmp_path, first["task_id"]) == first
    assert len(list_tasks(tmp_path)) == 2
    assert len(list_tasks(tmp_path, status="OPEN")) == 2


def test_complete_task(tmp_path: Path) -> None:
    task = create_task(
        case_root=tmp_path,
        case_id="LK-TEST-001",
        task_type="FOUNDER_APPROVAL",
        title="Founder approval",
        instructions="Approve or reject publication.",
        source_agent="LK-QA",
    )

    completed = complete_task(
        case_root=tmp_path,
        task_id=task["task_id"],
        completed_by="Founder",
        completion_note="Approved.",
    )

    assert completed["status"] == "COMPLETE"
    assert completed["completed_by"] == "Founder"
    assert completed["completed_at_utc"]
    assert blocking_tasks_open(tmp_path) is False


def test_cancel_task(tmp_path: Path) -> None:
    task = create_task(
        case_root=tmp_path,
        case_id="LK-TEST-001",
        task_type="TAMIL_LANGUAGE_REVIEW",
        title="Tamil review",
        instructions="Review Tamil language.",
        source_agent="LK-KURAL",
    )

    cancelled = cancel_task(
        case_root=tmp_path,
        task_id=task["task_id"],
        completed_by="Editor",
        completion_note="Superseded.",
    )

    assert cancelled["status"] == "CANCELLED"
    assert blocking_tasks_open(tmp_path) is False


def test_nonblocking_task_does_not_block(tmp_path: Path) -> None:
    create_task(
        case_root=tmp_path,
        case_id="LK-TEST-001",
        task_type="LEGAL_FIDELITY_REVIEW",
        title="Optional second review",
        instructions="Perform optional review.",
        source_agent="LK-QA",
        blocking=False,
    )

    assert blocking_tasks_open(tmp_path) is False


def test_invalid_task_type_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        create_task(
            case_root=tmp_path,
            case_id="LK-TEST-001",
            task_type="UNKNOWN",
            title="Unknown",
            instructions="Unknown task.",
            source_agent="LK-QA",
        )


def test_completed_task_cannot_complete_again(
    tmp_path: Path,
) -> None:
    task = create_task(
        case_root=tmp_path,
        case_id="LK-TEST-001",
        task_type="FOUNDER_APPROVAL",
        title="Founder approval",
        instructions="Approve publication.",
        source_agent="LK-QA",
    )

    complete_task(
        case_root=tmp_path,
        task_id=task["task_id"],
        completed_by="Founder",
        completion_note="Approved.",
    )

    with pytest.raises(ValueError):
        complete_task(
            case_root=tmp_path,
            task_id=task["task_id"],
            completed_by="Founder",
            completion_note="Approved again.",
        )
