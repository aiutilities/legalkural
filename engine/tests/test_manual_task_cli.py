from pathlib import Path

import pytest

from aidpl.manual_task_cli import build_parser, run
from aidpl.manual_tasks import create_task, get_task


def parse(*arguments: str):
    return build_parser().parse_args(list(arguments))


def test_list_open_tasks(tmp_path: Path) -> None:
    create_task(
        case_root=tmp_path,
        case_id="LK-B12-0001",
        task_type="LEGAL_FIDELITY_REVIEW",
        title="Review legal fidelity",
        instructions="Review source fidelity.",
        source_agent="LK-QA",
    )

    args = parse(
        "list",
        "--case-root",
        str(tmp_path),
        "--status",
        "OPEN",
    )

    result = run(args)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["status"] == "OPEN"


def test_show_task(tmp_path: Path) -> None:
    task = create_task(
        case_root=tmp_path,
        case_id="LK-B12-0002",
        task_type="TAMIL_LANGUAGE_REVIEW",
        title="Tamil review",
        instructions="Review Tamil language.",
        source_agent="LK-KURAL",
    )

    result = run(
        parse(
            "show",
            "--case-root",
            str(tmp_path),
            "--task-id",
            task["task_id"],
        )
    )

    assert result["task_id"] == task["task_id"]
    assert result["task_type"] == "TAMIL_LANGUAGE_REVIEW"


def test_complete_task_from_cli(tmp_path: Path) -> None:
    task = create_task(
        case_root=tmp_path,
        case_id="LK-B12-0003",
        task_type="FOUNDER_APPROVAL",
        title="Founder approval",
        instructions="Approve or reject publication.",
        source_agent="LK-QA",
    )

    result = run(
        parse(
            "complete",
            "--case-root",
            str(tmp_path),
            "--task-id",
            task["task_id"],
            "--completed-by",
            "Founder",
            "--note",
            "Publication approval reviewed and recorded.",
        )
    )

    assert result["status"] == "COMPLETE"
    assert result["completed_by"] == "Founder"
    assert (
        result["completion_note"]
        == "Publication approval reviewed and recorded."
    )

    stored = get_task(
        tmp_path,
        task["task_id"],
    )

    assert stored["status"] == "COMPLETE"


def test_cancel_task_from_cli(tmp_path: Path) -> None:
    task = create_task(
        case_root=tmp_path,
        case_id="LK-B12-0004",
        task_type="EDITORIAL_REVIEW",
        title="Editorial review",
        instructions="Review article.",
        source_agent="LK-EDITOR",
    )

    result = run(
        parse(
            "cancel",
            "--case-root",
            str(tmp_path),
            "--task-id",
            task["task_id"],
            "--completed-by",
            "Editor",
            "--note",
            "Task superseded by replacement review.",
        )
    )

    assert result["status"] == "CANCELLED"
    assert result["completed_by"] == "Editor"


def test_complete_requires_identity_and_note() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "complete",
                "--case-root",
                "/tmp/case",
                "--task-id",
                "MT-TEST",
            ]
        )


def test_invalid_status_rejected() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "list",
                "--case-root",
                "/tmp/case",
                "--status",
                "INVALID",
            ]
        )


def test_missing_task_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        run(
            parse(
                "show",
                "--case-root",
                str(tmp_path),
                "--task-id",
                "MT-NOT-FOUND",
            )
        )


def test_completed_task_cannot_be_completed_again(
    tmp_path: Path,
) -> None:
    task = create_task(
        case_root=tmp_path,
        case_id="LK-B12-0005",
        task_type="FOUNDER_APPROVAL",
        title="Founder approval",
        instructions="Approve publication.",
        source_agent="LK-QA",
    )

    command = [
        "complete",
        "--case-root",
        str(tmp_path),
        "--task-id",
        task["task_id"],
        "--completed-by",
        "Founder",
        "--note",
        "Approved.",
    ]

    run(parse(*command))

    with pytest.raises(ValueError):
        run(parse(*command))
