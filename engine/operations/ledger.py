"""Append-only production-operation ledger and explicit resume planning."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Mapping
from jsonschema import Draft202012Validator
from .workspace import load_production_workspace

LEDGER_SCHEMA_VERSION = "1.0"
OPERATION_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*$")
OPERATION_TYPES = {"INTEGRITY_AUDIT", "BACKUP", "RESTORE"}
ACTIVE_STATES = {"STARTED", "CHECKPOINTED"}
TERMINAL_STATES = {"COMPLETED", "FAILED"}
EVENT_WIDTH = 6
EVENT_FILE = "event.json"

class ProductionOperationLedgerError(ValueError):
    """Raised when an operation ledger is unsafe or invalid."""

def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()

def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def compute_operation_input_sha256(inputs: Mapping[str, Any]) -> str:
    if not isinstance(inputs, Mapping):
        raise ProductionOperationLedgerError("operation inputs must be an object")
    return _sha(_canonical(dict(inputs)))

def compute_operation_event_sha256(event: Mapping[str, Any]) -> str:
    value = deepcopy(dict(event)); value.pop("event_sha256", None)
    return _sha(_canonical(value))

def _schema() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "schemas" / "production_operation_event.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))

def validate_production_operation_event(event: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        raise ProductionOperationLedgerError("operation event must be an object")
    value = deepcopy(dict(event))
    errors = sorted(Draft202012Validator(_schema()).iter_errors(value), key=lambda e: list(e.absolute_path))
    if errors:
        raise ProductionOperationLedgerError(f"operation event is invalid: {errors[0].message}")
    if value["input_sha256"] != compute_operation_input_sha256(value["inputs"]):
        raise ProductionOperationLedgerError("operation input sha256 does not match")
    if value["event_sha256"] != compute_operation_event_sha256(value):
        raise ProductionOperationLedgerError("operation event sha256 does not match")
    state = value["state"]
    if state == "STARTED" and any(
        value[field] is not None for field in ("checkpoint", "result", "error")
    ):
        raise ProductionOperationLedgerError("STARTED event payload is invalid")
    if state == "CHECKPOINTED" and (
        value["checkpoint"] is None
        or value["result"] is not None
        or value["error"] is not None
    ):
        raise ProductionOperationLedgerError("CHECKPOINTED event payload is invalid")
    if state == "COMPLETED" and (
        value["result"] is None
        or value["checkpoint"] is not None
        or value["error"] is not None
    ):
        raise ProductionOperationLedgerError("COMPLETED event payload is invalid")
    if state == "FAILED" and (
        not isinstance(value["error"], str)
        or not value["error"].strip()
        or value["checkpoint"] is not None
        or value["result"] is not None
    ):
        raise ProductionOperationLedgerError("FAILED event payload is invalid")
    return value

def _utc(value: str) -> str:
    try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc: raise ProductionOperationLedgerError("occurred_at_utc is invalid") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ProductionOperationLedgerError("occurred_at_utc must be UTC")
    return value

def _root(workspace_root: Path, create: bool) -> Path:
    workspace = load_production_workspace(workspace_root)
    root = Path(workspace["paths"]["operator_logs"]) / "operations"
    if root.is_symlink(): raise ProductionOperationLedgerError("operation ledger root cannot be a symlink")
    if create: root.mkdir(exist_ok=True)
    if not root.exists(): return root
    if not root.is_dir(): raise ProductionOperationLedgerError("operation ledger root is unsafe")
    return root

def _operation(root: Path, operation_id: str) -> Path:
    if not isinstance(operation_id, str) or not OPERATION_ID_PATTERN.fullmatch(operation_id):
        raise ProductionOperationLedgerError("operation_id is invalid")
    path = root / operation_id
    if path.is_symlink(): raise ProductionOperationLedgerError("operation directory cannot be a symlink")
    return path

def list_operation_events(workspace_root: Path, operation_id: str) -> list[dict[str, Any]]:
    root = _root(workspace_root, False); operation = _operation(root, operation_id)
    if not operation.exists(): return []
    if not operation.is_dir(): raise ProductionOperationLedgerError("operation path is unsafe")
    events = operation / "events"
    if events.is_symlink() or not events.is_dir(): raise ProductionOperationLedgerError("operation events path is unsafe")
    directories = sorted(events.iterdir(), key=lambda p: p.name)
    result=[]; previous=None
    for number, directory in enumerate(directories, 1):
        expected=f"{number:0{EVENT_WIDTH}d}"
        if directory.is_symlink() or not directory.is_dir() or directory.name != expected:
            raise ProductionOperationLedgerError("operation event sequence is invalid")
        members=list(directory.iterdir())
        if len(members)!=1 or members[0].name!=EVENT_FILE or members[0].is_symlink():
            raise ProductionOperationLedgerError("operation event directory is incomplete")
        try: event=json.loads(members[0].read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: raise ProductionOperationLedgerError("operation event is unreadable") from exc
        validate_production_operation_event(event)
        if event["operation_id"]!=operation_id or event["event_number"]!=number:
            raise ProductionOperationLedgerError("operation event identity does not match path")
        if event["previous_event_sha256"] != previous:
            raise ProductionOperationLedgerError("operation event hash chain is broken")
        if result and (event["operation_type"]!=result[0]["operation_type"] or event["inputs"]!=result[0]["inputs"] or event["input_sha256"]!=result[0]["input_sha256"] or event["actor"]!=result[0]["actor"]):
            raise ProductionOperationLedgerError("immutable operation field changed")
        if result and result[-1]["state"] in TERMINAL_STATES:
            raise ProductionOperationLedgerError("terminal operation has later events")
        previous=event["event_sha256"]; result.append(event)
    return result

def _append(*, workspace_root: Path, operation_id: str, operation_type: str|None, state: str, actor: str|None, occurred_at_utc: str, inputs: Mapping[str,Any]|None, checkpoint: Mapping[str,Any]|None=None, result: Mapping[str,Any]|None=None, error: str|None=None) -> dict[str,Any]:
    _utc(occurred_at_utc); root=_root(workspace_root, True); operation=_operation(root,operation_id)
    prior=list_operation_events(workspace_root,operation_id)
    created_operation = not prior
    if not prior:
        if state!="STARTED": raise ProductionOperationLedgerError("first operation event must be STARTED")
        if operation_type not in OPERATION_TYPES: raise ProductionOperationLedgerError("operation_type is invalid")
        if not isinstance(actor,str) or not actor.strip(): raise ProductionOperationLedgerError("actor is invalid")
        if not isinstance(inputs,Mapping): raise ProductionOperationLedgerError("operation inputs must be an object")
        operation.mkdir(); (operation/"events").mkdir()
        base_inputs=deepcopy(dict(inputs)); base_type=operation_type; base_actor=actor
    else:
        if state == "STARTED":
            raise ProductionOperationLedgerError("operation_id already exists")
        if prior[-1]["state"] in TERMINAL_STATES: raise ProductionOperationLedgerError("operation is already terminal")
        base_inputs=prior[0]["inputs"]; base_type=prior[0]["operation_type"]; base_actor=prior[0]["actor"]
    number=len(prior)+1
    event={"schema_version":LEDGER_SCHEMA_VERSION,"operation_id":operation_id,"event_number":number,"previous_event_sha256":prior[-1]["event_sha256"] if prior else None,"operation_type":base_type,"state":state,"actor":base_actor,"occurred_at_utc":occurred_at_utc,"inputs":base_inputs,"input_sha256":compute_operation_input_sha256(base_inputs),"checkpoint":deepcopy(dict(checkpoint)) if checkpoint is not None else None,"result":deepcopy(dict(result)) if result is not None else None,"error":error,"provider_requests":0,"wordpress_requests":0,"tamil_rendered":False,"thirukkural_algorithm_usage":"TITLE_ONLY"}
    event["event_sha256"]=compute_operation_event_sha256(event); validate_production_operation_event(event)
    events=operation/"events"; target=events/f"{number:0{EVENT_WIDTH}d}"
    temporary=Path(tempfile.mkdtemp(prefix=".operation-tmp-",dir=events))
    try:
        output=temporary/EVENT_FILE
        with output.open("x",encoding="utf-8") as handle:
            json.dump(event,handle,ensure_ascii=False,indent=2,sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.rename(temporary,target); descriptor=os.open(events,os.O_RDONLY)
        try: os.fsync(descriptor)
        finally: os.close(descriptor)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        if created_operation:
            shutil.rmtree(operation, ignore_errors=True)
        raise
    return deepcopy(event)

def begin_operation(*,workspace_root:Path,operation_id:str,operation_type:str,actor:str,occurred_at_utc:str,inputs:Mapping[str,Any])->dict[str,Any]:
    return _append(workspace_root=workspace_root,operation_id=operation_id,operation_type=operation_type,state="STARTED",actor=actor,occurred_at_utc=occurred_at_utc,inputs=inputs)
def record_operation_checkpoint(*,workspace_root:Path,operation_id:str,occurred_at_utc:str,checkpoint:Mapping[str,Any])->dict[str,Any]:
    return _append(workspace_root=workspace_root,operation_id=operation_id,operation_type=None,state="CHECKPOINTED",actor=None,occurred_at_utc=occurred_at_utc,inputs=None,checkpoint=checkpoint)
def complete_operation(*,workspace_root:Path,operation_id:str,occurred_at_utc:str,result:Mapping[str,Any])->dict[str,Any]:
    return _append(workspace_root=workspace_root,operation_id=operation_id,operation_type=None,state="COMPLETED",actor=None,occurred_at_utc=occurred_at_utc,inputs=None,result=result)
def fail_operation(*,workspace_root:Path,operation_id:str,occurred_at_utc:str,error:str)->dict[str,Any]:
    if not isinstance(error,str) or not error.strip(): raise ProductionOperationLedgerError("error is invalid")
    return _append(workspace_root=workspace_root,operation_id=operation_id,operation_type=None,state="FAILED",actor=None,occurred_at_utc=occurred_at_utc,inputs=None,error=error)
def inspect_operation(workspace_root:Path,operation_id:str)->dict[str,Any]:
    events=list_operation_events(workspace_root,operation_id)
    if not events: raise ProductionOperationLedgerError(f"operation does not exist: {operation_id}")
    return {"operation_id":operation_id,"operation_type":events[0]["operation_type"],"state":events[-1]["state"],"event_count":len(events),"input_sha256":events[0]["input_sha256"],"latest_event_sha256":events[-1]["event_sha256"]}
def list_operations(workspace_root:Path)->dict[str,Any]:
    root=_root(workspace_root,False)
    if not root.exists(): return {"schema_version":"1.0","operation_count":0,"operations":[]}
    operations=[]
    for entry in sorted(root.iterdir(),key=lambda path:path.name):
        if entry.is_symlink() or not entry.is_dir() or not OPERATION_ID_PATTERN.fullmatch(entry.name):
            raise ProductionOperationLedgerError(f"unexpected operation ledger entry: {entry.name}")
        operations.append(inspect_operation(workspace_root,entry.name))
    return {"schema_version":"1.0","operation_count":len(operations),"operations":operations}
def plan_operation_resume(workspace_root:Path,operation_id:str)->dict[str,Any]:
    events=list_operation_events(workspace_root,operation_id)
    if not events: raise ProductionOperationLedgerError(f"operation does not exist: {operation_id}")
    if events[-1]["state"]=="COMPLETED": raise ProductionOperationLedgerError("completed operation cannot be resumed")
    checkpoint=next((event["checkpoint"] for event in reversed(events) if event["checkpoint"] is not None),None)
    return {"status":"RESUMABLE","operation_id":operation_id,"operation_type":events[0]["operation_type"],"inputs":deepcopy(events[0]["inputs"]),"input_sha256":events[0]["input_sha256"],"last_verified_state":events[-1]["state"],"last_verified_checkpoint":deepcopy(checkpoint),"next_event_number":len(events)+1,"executes_operation":False,"provider_requests":0,"wordpress_requests":0}
