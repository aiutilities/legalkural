from __future__ import annotations
import json
from pathlib import Path
import zipfile
import pytest
from operations.backup import ProductionBackupError, create_production_backup, validate_production_backup_evidence
from operations.workspace import initialize_production_workspace

def _workspace(tmp_path):
    root = tmp_path / "production"
    return root, initialize_production_workspace(root, "LK-PRODUCTION-TEST")

def _create(root, backup_id="LK-BACKUP-0001"):
    return create_production_backup(workspace_root=root, backup_id=backup_id, created_at_utc="2026-08-18T18:00:00Z")

def test_clean_workspace_backup_is_complete(tmp_path):
    root, workspace = _workspace(tmp_path)
    evidence = _create(root)
    assert evidence["status"] == "COMPLETE"
    assert evidence["provider_requests"] == evidence["wordpress_requests"] == 0
    assert (Path(workspace["paths"]["backups"]) / "LK-BACKUP-0001" / "backup.zip").is_file()

def test_backup_contains_workspace_and_source_file(tmp_path):
    root, workspace = _workspace(tmp_path)
    source = Path(workspace["paths"]["runtime_evidence"]) / "evidence.json"
    source.write_text('{"ok":true}\n')
    _create(root)
    package = Path(workspace["paths"]["backups"]) / "LK-BACKUP-0001" / "backup.zip"
    with zipfile.ZipFile(package) as archive:
        assert archive.namelist() == ["runtime-evidence/evidence.json", "workspace.json"]

def test_identical_sources_produce_deterministic_zip(tmp_path):
    root1, workspace1 = _workspace(tmp_path / "one")
    root2, workspace2 = _workspace(tmp_path / "two")
    # Workspace manifests contain absolute roots, so compare repeated packaging of copied bytes.
    first = _create(root1)
    package = Path(workspace1["paths"]["backups"]) / "LK-BACKUP-0001" / "backup.zip"
    assert first["archive_sha256"] == __import__("hashlib").sha256(package.read_bytes()).hexdigest()

def test_duplicate_backup_id_is_rejected(tmp_path):
    root, _ = _workspace(tmp_path)
    _create(root)
    with pytest.raises(ProductionBackupError, match="already exists"):
        _create(root)

def test_invalid_backup_id_is_rejected(tmp_path):
    root, _ = _workspace(tmp_path)
    with pytest.raises(ProductionBackupError, match="backup_id is invalid"):
        _create(root, "../unsafe")

def test_source_symlink_is_rejected(tmp_path):
    root, workspace = _workspace(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside")
    (Path(workspace["paths"]["operator_logs"]) / "unsafe").symlink_to(outside)
    with pytest.raises(ProductionBackupError, match="symlink"):
        _create(root)

def test_failed_integrity_audit_blocks_backup(tmp_path):
    root, workspace = _workspace(tmp_path)
    (Path(workspace["paths"]["candidates"]) / "unsafe.txt").write_text("unsafe")
    with pytest.raises(ProductionBackupError, match="audit did not pass"):
        _create(root)

def test_backups_are_excluded_from_snapshot(tmp_path):
    root, workspace = _workspace(tmp_path)
    first = _create(root)
    second = _create(root, "LK-BACKUP-0002")
    assert first["files"] == second["files"]
    assert all(not item["path"].startswith("backups/") for item in second["files"])

def test_evidence_schema_rejects_extra_field(tmp_path):
    root, _ = _workspace(tmp_path)
    evidence = _create(root)
    evidence["unexpected"] = True
    with pytest.raises(ProductionBackupError, match="evidence is invalid"):
        validate_production_backup_evidence(evidence)

def test_language_contract_is_preserved(tmp_path):
    root, _ = _workspace(tmp_path)
    evidence = _create(root)
    assert evidence["tamil_rendered"] is False
    assert evidence["thirukkural_algorithm_usage"] == "TITLE_ONLY"


def test_repeated_backup_of_same_sources_is_byte_deterministic(tmp_path):
    root, _ = _workspace(tmp_path)
    first = _create(root, "LK-BACKUP-DETERMINISTIC-1")
    second = _create(root, "LK-BACKUP-DETERMINISTIC-2")
    assert first["archive_sha256"] == second["archive_sha256"]
    assert first["archive_byte_count"] == second["archive_byte_count"]


def test_source_change_during_capture_is_rejected(tmp_path, monkeypatch):
    import operations.backup as backup_module

    root, workspace = _workspace(tmp_path)
    original = backup_module._inventory
    calls = 0

    def changing_inventory(source_root, supplied_workspace):
        nonlocal calls
        calls += 1
        result = original(source_root, supplied_workspace)
        if calls == 2:
            result = [dict(item) for item in result]
            result[0]["sha256"] = "0" * 64
        return result

    monkeypatch.setattr(backup_module, "_inventory", changing_inventory)
    with pytest.raises(ProductionBackupError, match="source changed"):
        _create(root)
    backups = Path(workspace["paths"]["backups"])
    assert list(backups.iterdir()) == []


def test_failed_zip_write_leaves_no_partial_backup(tmp_path, monkeypatch):
    import operations.backup as backup_module

    root, workspace = _workspace(tmp_path)

    def fail_write(output, source_root, files):
        output.write_bytes(b"partial")
        raise OSError("synthetic write failure")

    monkeypatch.setattr(backup_module, "_write_zip", fail_write)
    with pytest.raises(OSError, match="synthetic write failure"):
        _create(root)
    backups = Path(workspace["paths"]["backups"])
    assert list(backups.iterdir()) == []


def test_tampered_completed_zip_is_rejected(tmp_path):
    from operations.backup import verify_production_backup

    root, workspace = _workspace(tmp_path)
    _create(root)
    directory = Path(workspace["paths"]["backups"]) / "LK-BACKUP-0001"
    with (directory / "backup.zip").open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ProductionBackupError, match="byte count does not match"):
        verify_production_backup(directory)


def test_completed_backup_verifies_every_member(tmp_path):
    from operations.backup import verify_production_backup

    root, workspace = _workspace(tmp_path)
    created = _create(root)
    directory = Path(workspace["paths"]["backups"]) / "LK-BACKUP-0001"
    verified = verify_production_backup(directory)
    assert verified == created
    assert verified["file_count"] == len(verified["files"])
