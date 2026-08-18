from pathlib import Path
import json
import pytest
from operations.backup import create_production_backup
from operations.integrity import audit_production_estate
from operations.restore import ProductionRestoreError, restore_production_backup, validate_production_restore_evidence
from operations.workspace import DEFAULT_DIRECTORIES, initialize_production_workspace, load_production_workspace

def _backup(tmp_path):
    root = tmp_path / "source"
    workspace = initialize_production_workspace(root, "LK-PRODUCTION-TEST")
    (Path(workspace["paths"]["operator_logs"]) / "operation.log").write_text("verified\n")
    create_production_backup(workspace_root=root, backup_id="LK-BACKUP-RESTORE", created_at_utc="2026-08-18T18:00:00Z")
    return root, workspace, Path(workspace["paths"]["backups"]) / "LK-BACKUP-RESTORE"

def _restore(backup, destination, restore_id="LK-RESTORE-0001"):
    return restore_production_backup(backup_directory=backup, destination_root=destination, restore_id=restore_id, restored_at_utc="2026-08-18T18:30:00Z")

def test_verified_backup_restores_into_new_destination(tmp_path):
    _, _, backup = _backup(tmp_path)
    destination = tmp_path / "restored"
    evidence = _restore(backup, destination)
    assert evidence["status"] == "VERIFIED"
    assert load_production_workspace(destination)["workspace_root"] == str(destination)
    assert audit_production_estate(destination)["status"] == "PASS"

def test_non_manifest_source_bytes_are_preserved(tmp_path):
    _, _, backup = _backup(tmp_path)
    destination = tmp_path / "restored"
    _restore(backup, destination)
    assert (destination / "operator-logs" / "operation.log").read_bytes() == b"verified\n"

def test_all_workspace_directories_are_recreated(tmp_path):
    _, _, backup = _backup(tmp_path)
    destination = tmp_path / "restored"
    _restore(backup, destination)
    assert all((destination / relative).is_dir() for relative in DEFAULT_DIRECTORIES.values())

def test_existing_destination_is_rejected(tmp_path):
    _, _, backup = _backup(tmp_path)
    destination = tmp_path / "restored"
    destination.mkdir()
    with pytest.raises(ProductionRestoreError, match="must not already exist"):
        _restore(backup, destination)

def test_relative_destination_is_rejected(tmp_path):
    _, _, backup = _backup(tmp_path)
    with pytest.raises(ProductionRestoreError, match="must be absolute"):
        _restore(backup, Path("relative"))

def test_symlink_destination_is_rejected(tmp_path):
    _, _, backup = _backup(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "restored"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ProductionRestoreError, match="must not already exist"):
        _restore(backup, link)

def test_tampered_backup_is_rejected_without_destination(tmp_path):
    _, _, backup = _backup(tmp_path)
    with (backup / "backup.zip").open("ab") as handle:
        handle.write(b"tamper")
    destination = tmp_path / "restored"
    with pytest.raises(ProductionRestoreError, match="backup is not verified"):
        _restore(backup, destination)
    assert not destination.exists()

def test_invalid_restore_id_is_rejected(tmp_path):
    _, _, backup = _backup(tmp_path)
    with pytest.raises(ProductionRestoreError, match="restore_id is invalid"):
        _restore(backup, tmp_path / "restored", "../unsafe")

def test_restore_evidence_is_durable(tmp_path):
    _, _, backup = _backup(tmp_path)
    destination = tmp_path / "restored"
    evidence = _restore(backup, destination)
    path = destination / "runtime-evidence" / "restore-LK-RESTORE-0001.json"
    assert validate_production_restore_evidence(json.loads(path.read_text())) == evidence

def test_restore_evidence_rejects_extra_field(tmp_path):
    _, _, backup = _backup(tmp_path)
    evidence = _restore(backup, tmp_path / "restored")
    evidence["unexpected"] = True
    with pytest.raises(ProductionRestoreError, match="evidence is invalid"):
        validate_production_restore_evidence(evidence)

def test_language_and_external_request_contract(tmp_path):
    _, _, backup = _backup(tmp_path)
    evidence = _restore(backup, tmp_path / "restored")
    assert evidence["provider_requests"] == evidence["wordpress_requests"] == 0
    assert evidence["tamil_rendered"] is False
    assert evidence["thirukkural_algorithm_usage"] == "TITLE_ONLY"


def test_path_traversal_member_is_rejected(tmp_path, monkeypatch):
    import hashlib
    import zipfile
    import operations.restore as restore_module

    _, _, backup = _backup(tmp_path)
    archive_path = backup / "backup.zip"
    payload = b"escape"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escape.txt", payload)
    evidence = {
        "archive_file": "backup.zip",
        "files": [{
            "path": "../escape.txt",
            "byte_count": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }],
        "backup_id": "LK-BACKUP-RESTORE",
        "evidence_sha256": "0" * 64,
        "workspace_id": "LK-PRODUCTION-TEST",
    }
    monkeypatch.setattr(
        restore_module,
        "verify_production_backup",
        lambda supplied: evidence,
    )
    destination = tmp_path / "restored"
    with pytest.raises(ProductionRestoreError, match="unsafe or undeclared"):
        _restore(backup, destination)
    assert not destination.exists()
    assert not (tmp_path / "escape.txt").exists()


def test_duplicate_zip_members_are_rejected(tmp_path, monkeypatch):
    import hashlib
    import warnings
    import zipfile
    import operations.restore as restore_module

    _, _, backup = _backup(tmp_path)
    archive_path = backup / "backup.zip"
    payload = b"duplicate"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("workspace.json", payload)
            archive.writestr("workspace.json", payload)
    evidence = {
        "archive_file": "backup.zip",
        "files": [{
            "path": "workspace.json",
            "byte_count": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }],
        "backup_id": "LK-BACKUP-RESTORE",
        "evidence_sha256": "0" * 64,
        "workspace_id": "LK-PRODUCTION-TEST",
    }
    monkeypatch.setattr(
        restore_module,
        "verify_production_backup",
        lambda supplied: evidence,
    )
    destination = tmp_path / "restored"
    with pytest.raises(ProductionRestoreError, match="duplicate members"):
        _restore(backup, destination)
    assert not destination.exists()


def test_extraction_failure_is_cleaned_atomically(tmp_path, monkeypatch):
    import operations.restore as restore_module

    _, _, backup = _backup(tmp_path)
    original = restore_module._write
    calls = 0

    def fail_after_first(path, data):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic extraction failure")
        return original(path, data)

    monkeypatch.setattr(restore_module, "_write", fail_after_first)
    destination = tmp_path / "restored"
    with pytest.raises(OSError, match="synthetic extraction failure"):
        _restore(backup, destination)
    assert not destination.exists()
    assert list(tmp_path.glob(".restored-restore-tmp-*")) == []


def test_rebased_manifest_contains_no_original_root(tmp_path):
    source, _, backup = _backup(tmp_path)
    destination = tmp_path / "restored"
    _restore(backup, destination)
    manifest_text = (destination / "workspace.json").read_text()
    manifest = json.loads(manifest_text)
    assert str(source) not in manifest_text
    assert manifest["workspace_root"] == str(destination)
    assert all(str(value).startswith(str(destination) + "/") for value in manifest["paths"].values())


def test_restore_evidence_distinguishes_manifest_hashes(tmp_path):
    _, _, backup = _backup(tmp_path)
    evidence = _restore(backup, tmp_path / "restored")
    assert evidence["original_manifest_sha256"] != evidence["rebased_manifest_sha256"]
