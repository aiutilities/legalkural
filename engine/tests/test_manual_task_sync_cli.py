import json
from pathlib import Path

from aidpl.manual_task_cli import build_parser, run
from aidpl.manual_tasks import list_tasks


def parse(*arguments: str):
    return build_parser().parse_args(list(arguments))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def prepare_kural_review_case(
    case_root: Path,
    case_id: str,
) -> None:
    write_json(
        case_root / "output/09-kural/kural-brief.json",
        {
            "reference_case_id": case_id,
            "status": "EDITORIAL_DRAFT_REQUIRES_REVIEW",
            "requires_human_editorial_review": True,
        },
    )


def test_sync_parser_contract(tmp_path: Path) -> None:
    args = parse(
        "sync",
        "--case-id",
        "LK-S53-B13-0001",
        "--case-root",
        str(tmp_path),
    )

    assert args.command == "sync"
    assert args.case_id == "LK-S53-B13-0001"
    assert args.case_root == tmp_path


def test_sync_creates_detected_task(tmp_path: Path) -> None:
    case_id = "LK-S53-B13-0002"

    prepare_kural_review_case(
        tmp_path,
        case_id,
    )

    result = run(
        parse(
            "sync",
            "--case-id",
            case_id,
            "--case-root",
            str(tmp_path),
        )
    )

    tasks = list_tasks(tmp_path)

    assert len(tasks) == 1
    assert tasks[0]["case_id"] == case_id
    assert tasks[0]["task_type"] == "KURAL_EDITORIAL_REVIEW"
    assert tasks[0]["status"] == "OPEN"

    assert result["detected"] == 1
    assert result["created"] == 1


def test_sync_is_idempotent(tmp_path: Path) -> None:
    case_id = "LK-S53-B13-0003"

    prepare_kural_review_case(
        tmp_path,
        case_id,
    )

    command = parse(
        "sync",
        "--case-id",
        case_id,
        "--case-root",
        str(tmp_path),
    )

    first = run(command)

    command = parse(
        "sync",
        "--case-id",
        case_id,
        "--case-root",
        str(tmp_path),
    )

    second = run(command)

    tasks = list_tasks(tmp_path)

    assert len(tasks) == 1
    assert first["created"] == 1
    assert second["created"] == 0


def test_sync_preserves_case_artifact(tmp_path: Path) -> None:
    case_id = "LK-S53-B13-0004"

    prepare_kural_review_case(
        tmp_path,
        case_id,
    )

    artifact = (
        tmp_path
        / "output/09-kural/kural-brief.json"
    )

    before = artifact.read_bytes()

    run(
        parse(
            "sync",
            "--case-id",
            case_id,
            "--case-root",
            str(tmp_path),
        )
    )

    after = artifact.read_bytes()

    assert before == after


def test_sync_with_no_requirements_creates_empty_store(
    tmp_path: Path,
) -> None:
    case_id = "LK-S53-B13-0005"

    result = run(
        parse(
            "sync",
            "--case-id",
            case_id,
            "--case-root",
            str(tmp_path),
        )
    )

    assert result["detected"] == 0
    assert result["created"] == 0
    assert list_tasks(tmp_path) == []
