from copy import deepcopy
import json
from pathlib import Path

import pytest

from operations.workspace import (
    OperationsWorkspaceError,
    initialize_production_workspace,
    load_production_workspace,
    validate_production_workspace,
)


def _payload(root: Path) -> dict:
    return {
        "schema_version": "1.0",
        "workspace_id": "LK-PRODUCTION-001",
        "workspace_root": str(root),
        "paths": {
            "generated_evidence": str(root / "generated-evidence"),
            "candidates": str(root / "candidates"),
            "editions": str(root / "editions"),
            "archive": str(root / "archive"),
            "backups": str(root / "backups"),
            "runtime_evidence": str(root / "runtime-evidence"),
            "operator_logs": str(root / "operator-logs"),
        },
    }


def test_workspace_is_initialized_and_loaded(tmp_path):
    root = tmp_path / "production"
    created = initialize_production_workspace(root, "LK-PRODUCTION-001")
    assert created == load_production_workspace(root)
    assert (root / "workspace.json").is_file()
    assert all(Path(path).is_dir() for path in created["paths"].values())


def test_workspace_root_must_be_absolute():
    with pytest.raises(OperationsWorkspaceError, match="absolute path"):
        initialize_production_workspace(Path("relative"), "LK-PRODUCTION-001")


def test_unexpected_manifest_field_is_rejected(tmp_path):
    payload = _payload(tmp_path.resolve())
    payload["unexpected"] = True
    with pytest.raises(OperationsWorkspaceError, match="schema validation"):
        validate_production_workspace(payload)


def test_overlapping_paths_are_rejected(tmp_path):
    payload = _payload(tmp_path.resolve())
    payload["paths"]["operator_logs"] = payload["paths"]["runtime_evidence"]
    with pytest.raises(OperationsWorkspaceError, match="overlap"):
        validate_production_workspace(payload)


def test_path_escape_is_rejected(tmp_path):
    root = (tmp_path / "production").resolve()
    payload = _payload(root)
    payload["paths"]["backups"] = str((tmp_path / "outside").resolve())
    with pytest.raises(OperationsWorkspaceError, match="strict descendant"):
        validate_production_workspace(payload)


def test_symlink_workspace_root_is_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "workspace-link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(OperationsWorkspaceError, match="symlink"):
        initialize_production_workspace(link, "LK-PRODUCTION-001")


def test_broken_symlink_workspace_root_is_rejected(tmp_path):
    link = tmp_path / "broken-workspace-link"
    link.symlink_to(
        tmp_path / "missing-target",
        target_is_directory=True,
    )
    with pytest.raises(OperationsWorkspaceError, match="symlink"):
        initialize_production_workspace(link, "LK-PRODUCTION-001")


def test_nonempty_workspace_is_rejected(tmp_path):
    root = tmp_path / "production"
    root.mkdir()
    (root / "unexpected.txt").write_text("unsafe", encoding="utf-8")
    with pytest.raises(OperationsWorkspaceError, match="must be empty"):
        initialize_production_workspace(root, "LK-PRODUCTION-001")


def test_tampered_manifest_root_is_rejected(tmp_path):
    root = tmp_path / "production"
    initialize_production_workspace(root, "LK-PRODUCTION-001")
    manifest = root / "workspace.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["workspace_root"] = str((tmp_path / "other").resolve())
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(OperationsWorkspaceError):
        load_production_workspace(root)
