import json
from pathlib import Path

import aidpl.runtime as runtime


def test_build_worker_command_for_intake(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "bin").mkdir(parents=True)

    command = runtime.build_worker_command(
        root=root,
        worker="aidpl-intake",
        case_id="LK-RUNTIME-TEST-0001",
        case_root=tmp_path / "case",
        plan_path=tmp_path / "plan.json",
        source_pdf=tmp_path / "judgment.pdf",
        overwrite=True,
    )

    assert command[0].endswith("aidpl-intake")
    assert "--overwrite" in command
    assert "--plan" in command


def test_build_worker_command_for_standard_worker(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "bin").mkdir(parents=True)

    command = runtime.build_worker_command(
        root=root,
        worker="aidpl-law",
        case_id="LK-RUNTIME-TEST-0002",
        case_root=tmp_path / "case",
        plan_path=tmp_path / "plan.json",
        source_pdf=tmp_path / "judgment.pdf",
        overwrite=False,
    )

    assert command[0].endswith("aidpl-law")
    assert "--overwrite" not in command
    assert "--case-root" in command


def test_write_json(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    runtime.write_json(path, {"status": "COMPLETE"})

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "COMPLETE"
