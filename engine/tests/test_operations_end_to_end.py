"""Sprint 58 offline production-operations end-to-end certification."""
import json
from pathlib import Path

from operations import cli


def _call(capsys, *arguments):
    code = cli.main(list(arguments))
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert captured.err == ""
    return json.loads(captured.out)


def _json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _lifecycle(tmp_path, capsys, *, with_resume=False):
    root = tmp_path / "production"
    initialized = _call(capsys, "workspace-init", "--workspace-root", str(root), "--workspace-id", "LK-PRODUCTION-E2E")
    inputs = _json(tmp_path / "inputs.json", {"scope": "production-estate"})
    result = _json(tmp_path / "result.json", {"status": "PASS"})
    operation_id = "LK-OPERATION-E2E-AUDIT"
    _call(capsys, "operation-begin", "--workspace-root", str(root), "--operation-id", operation_id, "--operation-type", "INTEGRITY_AUDIT", "--actor", "Founder", "--occurred-at-utc", "2026-08-18T23:00:00Z", "--inputs-json-file", str(inputs))
    audit = _call(capsys, "audit", "--workspace-root", str(root))
    _call(capsys, "operation-complete", "--workspace-root", str(root), "--operation-id", operation_id, "--occurred-at-utc", "2026-08-18T23:01:00Z", "--result-json-file", str(result))
    resume = None
    if with_resume:
        pending = "LK-OPERATION-E2E-PENDING"
        _call(capsys, "operation-begin", "--workspace-root", str(root), "--operation-id", pending, "--operation-type", "BACKUP", "--actor", "Founder", "--occurred-at-utc", "2026-08-18T23:01:30Z", "--inputs-json-file", str(inputs))
        resume = _call(capsys, "operation-resume-plan", "--workspace-root", str(root), "--operation-id", pending)
    backup_created = _call(capsys, "backup-create", "--workspace-root", str(root), "--backup-id", "LK-BACKUP-E2E", "--created-at-utc", "2026-08-18T23:02:00Z")
    backup = Path(initialized["paths"]["backups"]) / "LK-BACKUP-E2E"
    backup_verified = _call(capsys, "backup-verify", "--backup-directory", str(backup))
    destination = tmp_path / "restored"
    restored = _call(capsys, "restore", "--backup-directory", str(backup), "--destination-root", str(destination), "--restore-id", "LK-RESTORE-E2E", "--restored-at-utc", "2026-08-18T23:03:00Z")
    restored_audit = _call(capsys, "audit", "--workspace-root", str(destination))
    release = _call(capsys, "release-certify", "--workspace-root", str(root), "--backup-directory", str(backup), "--release-id", "LK-RELEASE-E2E", "--certified-by", "Founder", "--certified-at-utc", "2026-08-18T23:04:00Z", "--source-commit", "b" * 40, "--required-operation-id", operation_id)
    return {"root": root, "destination": destination, "initialized": initialized, "audit": audit, "backup_created": backup_created, "backup_verified": backup_verified, "restored": restored, "restored_audit": restored_audit, "release": release, "resume": resume}


def test_complete_public_cli_lifecycle_is_offline_and_verified(tmp_path, capsys):
    values = _lifecycle(tmp_path, capsys)
    assert values["audit"]["status"] == "PASS"
    assert values["restored_audit"]["status"] == "PASS"
    assert values["backup_created"] == values["backup_verified"]
    assert values["restored"]["status"] == "VERIFIED"
    assert values["release"]["status"] == "READY"
    assert values["release"]["provider_requests"] == 0
    assert values["release"]["wordpress_requests"] == 0


def test_restored_estate_preserves_identity_not_physical_root(tmp_path, capsys):
    values = _lifecycle(tmp_path, capsys)
    assert values["restored"]["workspace_id"] == values["initialized"]["workspace_id"]
    assert values["root"].resolve() != values["destination"].resolve()
    assert values["backup_verified"]["evidence_sha256"] == values["restored"]["backup_evidence_sha256"]


def test_resume_plan_never_executes_and_project_contract_is_preserved(tmp_path, capsys):
    values = _lifecycle(tmp_path, capsys, with_resume=True)
    assert values["resume"]["executes_operation"] is False
    assert values["release"]["tamil_rendered"] is False
    assert values["release"]["thirukkural_algorithm_usage"] == "TITLE_ONLY"
    assert values["release"]["public_launch_authorized"] is False
