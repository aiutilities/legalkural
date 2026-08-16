import json
from pathlib import Path

from aidpl.manual_task_detection import (
    create_detected_tasks,
    detect_required_tasks,
)
from aidpl.manual_tasks import list_tasks


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def test_detects_kural_human_review(tmp_path: Path) -> None:
    case_root = tmp_path / "case"

    write_json(
        case_root / "output/09-kural/kural-brief.json",
        {
            "requires_human_editorial_review": True,
        },
    )

    tasks = detect_required_tasks(
        "LK-B11-0001",
        case_root,
    )

    assert len(tasks) == 1
    assert tasks[0]["task_type"] == "KURAL_EDITORIAL_REVIEW"
    assert tasks[0]["blocking"] is True


def test_no_kural_task_when_review_not_required(
    tmp_path: Path,
) -> None:
    case_root = tmp_path / "case"

    write_json(
        case_root / "output/09-kural/kural-brief.json",
        {
            "requires_human_editorial_review": False,
        },
    )

    assert detect_required_tasks(
        "LK-B11-0002",
        case_root,
    ) == []


def test_detects_qa_review_required(tmp_path: Path) -> None:
    case_root = tmp_path / "case"

    write_json(
        case_root / "evidence/validation-report.json",
        {
            "verdict": "REVIEW_REQUIRED",
            "publication_ready": False,
        },
    )

    tasks = detect_required_tasks(
        "LK-B11-0003",
        case_root,
    )

    assert len(tasks) == 1
    assert tasks[0]["task_type"] == "QA_REVIEW"


def test_detects_pass_without_publication_ready(
    tmp_path: Path,
) -> None:
    case_root = tmp_path / "case"

    write_json(
        case_root / "evidence/validation-report.json",
        {
            "verdict": "PASS",
            "publication_ready": False,
        },
    )

    tasks = detect_required_tasks(
        "LK-B11-0004",
        case_root,
    )

    assert len(tasks) == 1
    assert (
        tasks[0]["task_type"]
        == "PUBLICATION_READINESS_REVIEW"
    )


def test_pass_and_publication_ready_creates_no_qa_task(
    tmp_path: Path,
) -> None:
    case_root = tmp_path / "case"

    write_json(
        case_root / "evidence/validation-report.json",
        {
            "verdict": "PASS",
            "publication_ready": True,
        },
    )

    assert detect_required_tasks(
        "LK-B11-0005",
        case_root,
    ) == []


def test_detection_is_read_only(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    artifact = case_root / "evidence/validation-report.json"

    write_json(
        artifact,
        {
            "verdict": "REVIEW_REQUIRED",
            "publication_ready": False,
        },
    )

    before = artifact.read_bytes()

    detect_required_tasks(
        "LK-B11-0006",
        case_root,
    )

    after = artifact.read_bytes()

    assert before == after


def test_create_detected_tasks_is_idempotent(
    tmp_path: Path,
) -> None:
    case_root = tmp_path / "case"
    task_store = tmp_path / "manual-task-store"

    write_json(
        case_root / "evidence/validation-report.json",
        {
            "verdict": "REVIEW_REQUIRED",
            "publication_ready": False,
        },
    )

    first = create_detected_tasks(
        "LK-B11-0007",
        case_root,
        task_store,
    )

    second = create_detected_tasks(
        "LK-B11-0007",
        case_root,
        task_store,
    )

    tasks = list_tasks(task_store)

    assert first["detected"] == 1
    assert first["created"] == 1
    assert second["detected"] == 1
    assert second["created"] == 0
    assert second["skipped_existing"] == 1
    assert len(tasks) == 1


def test_multiple_review_requirements_create_distinct_tasks(
    tmp_path: Path,
) -> None:
    case_root = tmp_path / "case"
    task_store = tmp_path / "manual-task-store"

    write_json(
        case_root / "output/09-kural/kural-brief.json",
        {
            "requires_human_editorial_review": True,
        },
    )

    write_json(
        case_root / "evidence/validation-report.json",
        {
            "verdict": "REVIEW_REQUIRED",
            "publication_ready": False,
        },
    )

    result = create_detected_tasks(
        "LK-B11-0008",
        case_root,
        task_store,
    )

    tasks = list_tasks(task_store)

    assert result["detected"] == 2
    assert result["created"] == 2
    assert len(tasks) == 2

    assert {
        task["task_type"]
        for task in tasks
    } == {
        "KURAL_EDITORIAL_REVIEW",
        "QA_REVIEW",
    }
