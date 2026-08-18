"""Security-gated production-readiness release evidence."""
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
from typing import Any, Mapping, Sequence
from jsonschema import Draft202012Validator
from .backup import _inventory, verify_production_backup
from .integrity import audit_production_estate
from .ledger import inspect_operation
from .workspace import load_production_workspace

RELEASE_SCHEMA_VERSION = "1.0"
RELEASE_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
PROHIBITED_EXACT = {".env", "id_rsa", "id_dsa", "credentials.json", "token.json"}
PROHIBITED_SUFFIXES = (".pem", ".key", ".p12", ".pfx")

class ProductionReleaseError(ValueError):
    """Raised when production readiness cannot be certified."""

def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
def compute_release_evidence_sha256(evidence: Mapping[str,Any])->str:
    value=deepcopy(dict(evidence)); value.pop("evidence_sha256",None); return _sha(_canonical(value))
def _schema()->dict[str,Any]:
    path=Path(__file__).resolve().parents[1]/"schemas"/"production_release_evidence.schema.json"; return json.loads(path.read_text(encoding="utf-8"))
def validate_production_release_evidence(evidence:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(evidence,Mapping): raise ProductionReleaseError("release evidence must be an object")
    value=deepcopy(dict(evidence)); errors=sorted(Draft202012Validator(_schema()).iter_errors(value),key=lambda e:list(e.absolute_path))
    if errors: raise ProductionReleaseError(f"release evidence is invalid: {errors[0].message}")
    if value["evidence_sha256"]!=compute_release_evidence_sha256(value): raise ProductionReleaseError("release evidence sha256 does not match content")
    return value
def _utc(value:str)->str:
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except (AttributeError,ValueError) as exc: raise ProductionReleaseError("certified_at_utc is invalid") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds()!=0: raise ProductionReleaseError("certified_at_utc must be UTC")
    return value
def _security_scan(workspace:Mapping[str,Any])->dict[str,Any]:
    scanned=0
    for name,value in sorted(workspace["paths"].items()):
        if name=="backups": continue
        base=Path(value)
        for path in sorted(base.rglob("*"),key=lambda p:p.as_posix()):
            if path.is_symlink(): raise ProductionReleaseError(f"security scan rejected symlink: {path}")
            if path.is_dir(): continue
            if not path.is_file(): raise ProductionReleaseError(f"security scan rejected unsupported file: {path}")
            lowered=path.name.lower()
            if lowered in PROHIBITED_EXACT or lowered.endswith(PROHIBITED_SUFFIXES):
                raise ProductionReleaseError(f"security scan rejected prohibited file: {path.name}")
            scanned+=1
    return {"status":"PASS","files_scanned":scanned,"prohibited_files":0}
def _write(path:Path,data:bytes)->None:
    with path.open("xb") as handle: handle.write(data); handle.flush(); os.fsync(handle.fileno())

def _release_chain(releases: Path) -> list[dict[str, Any]]:
    if not releases.exists():
        return []
    if releases.is_symlink() or not releases.is_dir():
        raise ProductionReleaseError("release evidence root is unsafe")
    evidence_items = []
    for entry in sorted(releases.iterdir(), key=lambda item: item.name):
        if entry.is_symlink() or not entry.is_dir() or not RELEASE_ID_PATTERN.fullmatch(entry.name):
            raise ProductionReleaseError(f"unexpected release evidence entry: {entry.name}")
        members = list(entry.iterdir())
        if len(members) != 1 or members[0].name != "release-evidence.json" or members[0].is_symlink():
            raise ProductionReleaseError("release evidence directory is incomplete")
        try:
            evidence = validate_production_release_evidence(
                json.loads(members[0].read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ProductionReleaseError("prior release evidence is unreadable") from exc
        if evidence["release_id"] != entry.name:
            raise ProductionReleaseError("release evidence identity does not match path")
        evidence_items.append(evidence)
    evidence_items.sort(key=lambda item: (item["certified_at_utc"], item["release_id"]))
    previous = None
    for evidence in evidence_items:
        if evidence["previous_release_evidence_sha256"] != previous:
            raise ProductionReleaseError("release evidence hash chain is broken")
        previous = evidence["evidence_sha256"]
    return evidence_items

def certify_production_release(*,workspace_root:Path,backup_directory:Path,release_id:str,certified_by:str,certified_at_utc:str,source_commit:str,required_operation_ids:Sequence[str])->dict[str,Any]:
    """Atomically record local production-readiness evidence."""
    if not isinstance(release_id,str) or not RELEASE_ID_PATTERN.fullmatch(release_id): raise ProductionReleaseError("release_id is invalid")
    if not isinstance(certified_by,str) or not certified_by.strip(): raise ProductionReleaseError("certified_by is invalid")
    _utc(certified_at_utc)
    if not isinstance(source_commit,str) or not COMMIT_PATTERN.fullmatch(source_commit): raise ProductionReleaseError("source_commit must be a 40-character lowercase SHA")
    if not isinstance(required_operation_ids,Sequence) or isinstance(required_operation_ids,(str,bytes)) or not required_operation_ids:
        raise ProductionReleaseError("required_operation_ids must be non-empty")
    if len(set(required_operation_ids))!=len(required_operation_ids): raise ProductionReleaseError("required_operation_ids contains duplicates")
    workspace=load_production_workspace(workspace_root)
    runtime=Path(workspace["paths"]["runtime_evidence"])
    releases=runtime/"releases"
    if releases.is_symlink():
        raise ProductionReleaseError("release evidence root cannot be a symlink")
    target=releases/release_id
    if target.exists() or target.is_symlink():
        raise ProductionReleaseError(f"release_id already exists: {release_id}")
    prior_releases = _release_chain(releases)
    if prior_releases:
        previous_time = datetime.fromisoformat(
            prior_releases[-1]["certified_at_utc"].replace("Z", "+00:00")
        )
        current_time = datetime.fromisoformat(
            certified_at_utc.replace("Z", "+00:00")
        )
        if current_time <= previous_time:
            raise ProductionReleaseError(
                "certified_at_utc must be later than prior release evidence"
            )
    audit=audit_production_estate(workspace_root)
    if audit["status"]!="PASS": raise ProductionReleaseError("production integrity audit did not pass")
    backup=verify_production_backup(backup_directory)
    if backup["workspace_id"]!=workspace["workspace_id"]: raise ProductionReleaseError("backup workspace_id does not match")
    if backup["files"]!=_inventory(Path(workspace["workspace_root"]),workspace): raise ProductionReleaseError("backup does not match current workspace")
    operations=[]
    for operation_id in required_operation_ids:
        inspected=inspect_operation(workspace_root,operation_id)
        if inspected["state"]!="COMPLETED": raise ProductionReleaseError(f"required operation is not completed: {operation_id}")
        operations.append(inspected)
    operations.sort(key=lambda item:item["operation_id"])
    security=_security_scan(workspace)
    releases.mkdir(exist_ok=True)
    evidence={"schema_version":RELEASE_SCHEMA_VERSION,"release_id":release_id,"workspace_id":workspace["workspace_id"],"certified_by":certified_by,"certified_at_utc":certified_at_utc,"source_commit":source_commit,"status":"READY","audit_status":"PASS","backup_id":backup["backup_id"],"backup_evidence_sha256":backup["evidence_sha256"],"previous_release_evidence_sha256":prior_releases[-1]["evidence_sha256"] if prior_releases else None,"required_operations":operations,"security_scan":security,"provider_requests":0,"wordpress_requests":0,"tamil_rendered":False,"thirukkural_algorithm_usage":"TITLE_ONLY","public_launch_authorized":False}
    evidence["evidence_sha256"]=compute_release_evidence_sha256(evidence); validate_production_release_evidence(evidence)
    temporary=Path(tempfile.mkdtemp(prefix=".release-tmp-",dir=releases))
    try:
        _write(temporary/"release-evidence.json",json.dumps(evidence,ensure_ascii=False,indent=2,sort_keys=True).encode()+b"\n")
        os.rename(temporary,target); descriptor=os.open(releases,os.O_RDONLY)
        try: os.fsync(descriptor)
        finally: os.close(descriptor)
    except Exception: shutil.rmtree(temporary,ignore_errors=True); raise
    return validate_production_release_evidence(json.loads((target/"release-evidence.json").read_text()))
