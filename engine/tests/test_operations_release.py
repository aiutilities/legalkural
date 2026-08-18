import json
from pathlib import Path
import pytest
from operations.backup import create_production_backup
from operations.ledger import begin_operation,complete_operation
from operations.release import ProductionReleaseError,certify_production_release,validate_production_release_evidence
from operations.workspace import initialize_production_workspace
COMMIT="a"*40
def _ready(tmp_path,state="COMPLETED"):
    root=tmp_path/"production"; workspace=initialize_production_workspace(root,"LK-PRODUCTION-TEST")
    begin_operation(workspace_root=root,operation_id="LK-OPERATION-RELEASE",operation_type="INTEGRITY_AUDIT",actor="Founder",occurred_at_utc="2026-08-18T20:00:00Z",inputs={})
    if state=="COMPLETED": complete_operation(workspace_root=root,operation_id="LK-OPERATION-RELEASE",occurred_at_utc="2026-08-18T20:01:00Z",result={"status":"PASS"})
    create_production_backup(workspace_root=root,backup_id="LK-BACKUP-RELEASE",created_at_utc="2026-08-18T20:02:00Z")
    backup=Path(workspace["paths"]["backups"])/"LK-BACKUP-RELEASE"; return root,workspace,backup
def _certify(root,backup,release_id="LK-RELEASE-0001"):
    return certify_production_release(workspace_root=root,backup_directory=backup,release_id=release_id,certified_by="Founder",certified_at_utc="2026-08-18T20:03:00Z",source_commit=COMMIT,required_operation_ids=["LK-OPERATION-RELEASE"])
def test_ready_workspace_is_certified(tmp_path):
    root,_,backup=_ready(tmp_path); evidence=_certify(root,backup); assert evidence["status"]=="READY"; assert evidence["public_launch_authorized"] is False
def test_release_evidence_is_durable(tmp_path):
    root,workspace,backup=_ready(tmp_path); evidence=_certify(root,backup); path=Path(workspace["paths"]["runtime_evidence"])/"releases"/"LK-RELEASE-0001"/"release-evidence.json"; assert validate_production_release_evidence(json.loads(path.read_text()))==evidence
def test_duplicate_release_id_is_rejected(tmp_path):
    root,_,backup=_ready(tmp_path); _certify(root,backup)
    with pytest.raises(ProductionReleaseError,match="already exists"): _certify(root,backup)
def test_invalid_source_commit_is_rejected(tmp_path):
    root,_,backup=_ready(tmp_path)
    with pytest.raises(ProductionReleaseError,match="40-character"): certify_production_release(workspace_root=root,backup_directory=backup,release_id="LK-RELEASE-0001",certified_by="Founder",certified_at_utc="2026-08-18T20:03:00Z",source_commit="short",required_operation_ids=["LK-OPERATION-RELEASE"])
def test_active_required_operation_is_rejected(tmp_path):
    root,_,backup=_ready(tmp_path,state="STARTED")
    with pytest.raises(ProductionReleaseError,match="not completed"): _certify(root,backup)
def test_backup_must_match_current_workspace(tmp_path):
    root,workspace,backup=_ready(tmp_path); (Path(workspace["paths"]["operator_logs"])/"changed.log").write_text("changed")
    with pytest.raises(ProductionReleaseError,match="does not match current workspace"): _certify(root,backup)
def test_prohibited_env_file_is_rejected(tmp_path):
    root,workspace,backup=_ready(tmp_path); env=Path(workspace["paths"]["runtime_evidence"])/".env"; env.write_text("SECRET=x"); create_production_backup(workspace_root=root,backup_id="LK-BACKUP-UPDATED",created_at_utc="2026-08-18T20:02:30Z"); updated=Path(workspace["paths"]["backups"])/"LK-BACKUP-UPDATED"
    with pytest.raises(ProductionReleaseError,match="prohibited file"): _certify(root,updated)
def test_private_key_suffix_is_rejected(tmp_path):
    root,workspace,backup=_ready(tmp_path); key=Path(workspace["paths"]["runtime_evidence"])/"private.key"; key.write_text("key"); create_production_backup(workspace_root=root,backup_id="LK-BACKUP-UPDATED",created_at_utc="2026-08-18T20:02:30Z"); updated=Path(workspace["paths"]["backups"])/"LK-BACKUP-UPDATED"
    with pytest.raises(ProductionReleaseError,match="prohibited file"): _certify(root,updated)
def test_empty_required_operations_is_rejected(tmp_path):
    root,_,backup=_ready(tmp_path)
    with pytest.raises(ProductionReleaseError,match="non-empty"): certify_production_release(workspace_root=root,backup_directory=backup,release_id="LK-RELEASE-0001",certified_by="Founder",certified_at_utc="2026-08-18T20:03:00Z",source_commit=COMMIT,required_operation_ids=[])
def test_duplicate_required_operations_is_rejected(tmp_path):
    root,_,backup=_ready(tmp_path)
    with pytest.raises(ProductionReleaseError,match="duplicates"): certify_production_release(workspace_root=root,backup_directory=backup,release_id="LK-RELEASE-0001",certified_by="Founder",certified_at_utc="2026-08-18T20:03:00Z",source_commit=COMMIT,required_operation_ids=["LK-OPERATION-RELEASE"]*2)
def test_evidence_schema_rejects_extra_field(tmp_path):
    root,_,backup=_ready(tmp_path); evidence=_certify(root,backup); evidence["unexpected"]=True
    with pytest.raises(ProductionReleaseError,match="evidence is invalid"): validate_production_release_evidence(evidence)
def test_project_contract_and_zero_requests(tmp_path):
    root,_,backup=_ready(tmp_path); evidence=_certify(root,backup); assert evidence["provider_requests"]==evidence["wordpress_requests"]==0; assert evidence["tamil_rendered"] is False; assert evidence["thirukkural_algorithm_usage"]=="TITLE_ONLY"


def test_release_evidence_forms_append_only_hash_chain(tmp_path):
    root, workspace, backup = _ready(tmp_path)
    first = _certify(root, backup, "LK-RELEASE-0001")
    create_production_backup(
        workspace_root=root,
        backup_id="LK-BACKUP-RELEASE-2",
        created_at_utc="2026-08-18T20:03:30Z",
    )
    second_backup = (
        Path(workspace["paths"]["backups"]) / "LK-BACKUP-RELEASE-2"
    )
    second = certify_production_release(
        workspace_root=root,
        backup_directory=second_backup,
        release_id="LK-RELEASE-0002",
        certified_by="Founder",
        certified_at_utc="2026-08-18T20:04:00Z",
        source_commit=COMMIT,
        required_operation_ids=["LK-OPERATION-RELEASE"],
    )
    assert first["previous_release_evidence_sha256"] is None
    assert second["previous_release_evidence_sha256"] == first["evidence_sha256"]


def test_tampered_prior_release_blocks_next_release(tmp_path):
    root, workspace, backup = _ready(tmp_path)
    _certify(root, backup)
    prior = (
        Path(workspace["paths"]["runtime_evidence"])
        / "releases" / "LK-RELEASE-0001" / "release-evidence.json"
    )
    value = json.loads(prior.read_text())
    value["certified_by"] = "Tampered"
    prior.write_text(json.dumps(value))
    with pytest.raises(ProductionReleaseError, match="sha256"):
        certify_production_release(
            workspace_root=root,
            backup_directory=backup,
            release_id="LK-RELEASE-0002",
            certified_by="Founder",
            certified_at_utc="2026-08-18T20:04:00Z",
            source_commit=COMMIT,
            required_operation_ids=["LK-OPERATION-RELEASE"],
        )


def test_failed_required_operation_is_rejected(tmp_path):
    from operations.ledger import fail_operation

    root = tmp_path / "production"
    workspace = initialize_production_workspace(root, "LK-PRODUCTION-TEST")
    begin_operation(
        workspace_root=root,
        operation_id="LK-OPERATION-RELEASE",
        operation_type="BACKUP",
        actor="Founder",
        occurred_at_utc="2026-08-18T20:00:00Z",
        inputs={},
    )
    fail_operation(
        workspace_root=root,
        operation_id="LK-OPERATION-RELEASE",
        occurred_at_utc="2026-08-18T20:01:00Z",
        error="failed",
    )
    create_production_backup(
        workspace_root=root,
        backup_id="LK-BACKUP-RELEASE",
        created_at_utc="2026-08-18T20:02:00Z",
    )
    backup = Path(workspace["paths"]["backups"]) / "LK-BACKUP-RELEASE"
    with pytest.raises(ProductionReleaseError, match="not completed"):
        _certify(root, backup)


def test_release_rename_failure_leaves_no_partial_evidence(
    tmp_path,
    monkeypatch,
):
    import operations.release as release_module

    root, workspace, backup = _ready(tmp_path)

    def fail_rename(source, target):
        raise OSError("synthetic release rename failure")

    monkeypatch.setattr(release_module.os, "rename", fail_rename)
    with pytest.raises(OSError, match="synthetic release rename failure"):
        _certify(root, backup)
    releases = Path(workspace["paths"]["runtime_evidence"]) / "releases"
    assert not (releases / "LK-RELEASE-0001").exists()
    assert list(releases.glob(".release-tmp-*")) == []
