import json
from pathlib import Path
import pytest
from operations.ledger import *
from operations.workspace import initialize_production_workspace

def _root(tmp_path):
    root=tmp_path/"production"; initialize_production_workspace(root,"LK-PRODUCTION-TEST"); return root
def _begin(root,operation_id="LK-OPERATION-0001"):
    return begin_operation(workspace_root=root,operation_id=operation_id,operation_type="BACKUP",actor="Founder",occurred_at_utc="2026-08-18T19:00:00Z",inputs={"backup_id":"LK-BACKUP-1"})
def test_begin_operation_creates_first_event(tmp_path):
    root=_root(tmp_path); event=_begin(root); assert event["state"]=="STARTED"; assert event["event_number"]==1
def test_checkpoint_and_completion_preserve_chain(tmp_path):
    root=_root(tmp_path); _begin(root); record_operation_checkpoint(workspace_root=root,operation_id="LK-OPERATION-0001",occurred_at_utc="2026-08-18T19:01:00Z",checkpoint={"step":"CAPTURED"}); complete_operation(workspace_root=root,operation_id="LK-OPERATION-0001",occurred_at_utc="2026-08-18T19:02:00Z",result={"status":"COMPLETE"}); events=list_operation_events(root,"LK-OPERATION-0001"); assert [e["state"] for e in events]==["STARTED","CHECKPOINTED","COMPLETED"]
def test_failed_operation_is_resumable(tmp_path):
    root=_root(tmp_path); _begin(root); fail_operation(workspace_root=root,operation_id="LK-OPERATION-0001",occurred_at_utc="2026-08-18T19:02:00Z",error="interrupted"); plan=plan_operation_resume(root,"LK-OPERATION-0001"); assert plan["status"]=="RESUMABLE"; assert plan["executes_operation"] is False
def test_checkpoint_is_in_resume_plan(tmp_path):
    root=_root(tmp_path); _begin(root); record_operation_checkpoint(workspace_root=root,operation_id="LK-OPERATION-0001",occurred_at_utc="2026-08-18T19:01:00Z",checkpoint={"step":"VERIFIED"}); plan=plan_operation_resume(root,"LK-OPERATION-0001"); assert plan["last_verified_checkpoint"]=={"step":"VERIFIED"}
def test_completed_operation_cannot_resume(tmp_path):
    root=_root(tmp_path); _begin(root); complete_operation(workspace_root=root,operation_id="LK-OPERATION-0001",occurred_at_utc="2026-08-18T19:02:00Z",result={});
    with pytest.raises(ProductionOperationLedgerError,match="cannot be resumed"): plan_operation_resume(root,"LK-OPERATION-0001")
def test_terminal_operation_rejects_later_event(tmp_path):
    root=_root(tmp_path); _begin(root); fail_operation(workspace_root=root,operation_id="LK-OPERATION-0001",occurred_at_utc="2026-08-18T19:02:00Z",error="failed")
    with pytest.raises(ProductionOperationLedgerError,match="already terminal"): record_operation_checkpoint(workspace_root=root,operation_id="LK-OPERATION-0001",occurred_at_utc="2026-08-18T19:03:00Z",checkpoint={})
def test_duplicate_operation_id_is_rejected(tmp_path):
    root=_root(tmp_path); _begin(root)
    with pytest.raises(ProductionOperationLedgerError): _begin(root)
def test_tampered_event_is_rejected(tmp_path):
    root=_root(tmp_path); _begin(root); path=next((root/"operator-logs"/"operations").rglob("event.json")); value=json.loads(path.read_text()); value["actor"]="Tampered"; path.write_text(json.dumps(value))
    with pytest.raises(ProductionOperationLedgerError,match="sha256"): list_operation_events(root,"LK-OPERATION-0001")
def test_missing_event_sequence_is_rejected(tmp_path):
    root=_root(tmp_path); _begin(root); record_operation_checkpoint(workspace_root=root,operation_id="LK-OPERATION-0001",occurred_at_utc="2026-08-18T19:01:00Z",checkpoint={}); shutil=__import__("shutil"); shutil.rmtree(root/"operator-logs"/"operations"/"LK-OPERATION-0001"/"events"/"000001")
    with pytest.raises(ProductionOperationLedgerError,match="sequence"): list_operation_events(root,"LK-OPERATION-0001")
def test_operation_symlink_is_rejected(tmp_path):
    root=_root(tmp_path); ledger=root/"operator-logs"/"operations"; ledger.mkdir(); outside=tmp_path/"outside"; outside.mkdir(); (ledger/"LK-OPERATION-0001").symlink_to(outside,target_is_directory=True)
    with pytest.raises(ProductionOperationLedgerError,match="symlink"): list_operation_events(root,"LK-OPERATION-0001")
def test_inspection_is_deterministic(tmp_path):
    root=_root(tmp_path); _begin(root); assert inspect_operation(root,"LK-OPERATION-0001")==inspect_operation(root,"LK-OPERATION-0001")
def test_operation_listing_is_sorted(tmp_path):
    root=_root(tmp_path); _begin(root,"LK-OPERATION-0002"); _begin(root,"LK-OPERATION-0001"); listing=list_operations(root); assert [item["operation_id"] for item in listing["operations"]]==["LK-OPERATION-0001","LK-OPERATION-0002"]
def test_unexpected_ledger_entry_is_rejected(tmp_path):
    root=_root(tmp_path); _begin(root); (root/"operator-logs"/"operations"/"unexpected.txt").write_text("unsafe")
    with pytest.raises(ProductionOperationLedgerError,match="unexpected operation ledger entry"): list_operations(root)
def test_project_contract_is_preserved(tmp_path):
    root=_root(tmp_path); event=_begin(root); plan=plan_operation_resume(root,"LK-OPERATION-0001"); assert event["tamil_rendered"] is False; assert event["thirukkural_algorithm_usage"]=="TITLE_ONLY"; assert plan["provider_requests"]==plan["wordpress_requests"]==0


def test_broken_previous_event_hash_is_rejected(tmp_path):
    root = _root(tmp_path)
    _begin(root)
    record_operation_checkpoint(
        workspace_root=root,
        operation_id="LK-OPERATION-0001",
        occurred_at_utc="2026-08-18T19:01:00Z",
        checkpoint={"step": "VERIFIED"},
    )
    path = (
        root / "operator-logs" / "operations" / "LK-OPERATION-0001"
        / "events" / "000002" / "event.json"
    )
    event = json.loads(path.read_text())
    event["previous_event_sha256"] = "0" * 64
    event["event_sha256"] = compute_operation_event_sha256(event)
    path.write_text(json.dumps(event))
    with pytest.raises(ProductionOperationLedgerError, match="hash chain is broken"):
        list_operation_events(root, "LK-OPERATION-0001")


def test_event_identity_path_mismatch_is_rejected(tmp_path):
    root = _root(tmp_path)
    _begin(root)
    path = next((root / "operator-logs" / "operations").rglob("event.json"))
    event = json.loads(path.read_text())
    event["operation_id"] = "LK-OPERATION-OTHER"
    event["event_sha256"] = compute_operation_event_sha256(event)
    path.write_text(json.dumps(event))
    with pytest.raises(ProductionOperationLedgerError, match="identity does not match"):
        list_operation_events(root, "LK-OPERATION-0001")


def test_failed_first_event_rename_leaves_no_operation_shell(
    tmp_path,
    monkeypatch,
):
    import operations.ledger as ledger_module

    root = _root(tmp_path)

    def fail_rename(source, target):
        raise OSError("synthetic rename failure")

    monkeypatch.setattr(ledger_module.os, "rename", fail_rename)
    with pytest.raises(OSError, match="synthetic rename failure"):
        _begin(root)
    operation = (
        root / "operator-logs" / "operations" / "LK-OPERATION-0001"
    )
    assert not operation.exists()


def test_state_specific_payload_is_enforced(tmp_path):
    root = _root(tmp_path)
    event = _begin(root)
    event["state"] = "CHECKPOINTED"
    event["event_sha256"] = compute_operation_event_sha256(event)
    with pytest.raises(
        ProductionOperationLedgerError,
        match="CHECKPOINTED event payload is invalid",
    ):
        validate_production_operation_event(event)


def test_resume_plan_preserves_original_inputs_and_hash(tmp_path):
    root = _root(tmp_path)
    started = begin_operation(
        workspace_root=root,
        operation_id="LK-OPERATION-0001",
        operation_type="RESTORE",
        actor="Founder",
        occurred_at_utc="2026-08-18T19:00:00Z",
        inputs={"destination": "/approved/restore", "backup_id": "LK-BACKUP-1"},
    )
    fail_operation(
        workspace_root=root,
        operation_id="LK-OPERATION-0001",
        occurred_at_utc="2026-08-18T19:01:00Z",
        error="interrupted",
    )
    plan = plan_operation_resume(root, "LK-OPERATION-0001")
    assert plan["inputs"] == started["inputs"]
    assert plan["input_sha256"] == started["input_sha256"]
    assert plan["operation_type"] == "RESTORE"
