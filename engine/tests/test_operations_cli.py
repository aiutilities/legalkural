import json
from pathlib import Path
import pytest
from operations import cli

def _run(argv, capsys):
    code=cli.main(argv); captured=capsys.readouterr(); return code,captured
def _init(tmp_path,capsys):
    root=tmp_path/"production"; code,captured=_run(["workspace-init","--workspace-root",str(root),"--workspace-id","LK-PRODUCTION-TEST"],capsys); assert code==0; return root,json.loads(captured.out)
def _json(tmp_path,name,value):
    path=tmp_path/name; path.write_text(json.dumps(value)); return path

def test_parser_exposes_all_operations_commands():
    parser=cli.build_parser(); choices=next(action for action in parser._actions if isinstance(action,__import__("argparse")._SubParsersAction)).choices
    assert set(choices)=={"workspace-init","audit","backup-create","backup-verify","restore","operation-begin","operation-checkpoint","operation-complete","operation-fail","operation-inspect","operation-list","operation-resume-plan","release-certify"}
def test_workspace_init_outputs_json(tmp_path,capsys):
    root,payload=_init(tmp_path,capsys); assert payload["workspace_root"]==str(root)
def test_audit_command_passes_clean_workspace(tmp_path,capsys):
    root,_=_init(tmp_path,capsys); code,captured=_run(["audit","--workspace-root",str(root)],capsys); assert code==0; assert json.loads(captured.out)["status"]=="PASS"
def test_backup_create_and_verify_commands(tmp_path,capsys):
    root,workspace=_init(tmp_path,capsys); code,created=_run(["backup-create","--workspace-root",str(root),"--backup-id","LK-BACKUP-CLI","--created-at-utc","2026-08-18T20:00:00Z"],capsys); assert code==0; backup=Path(workspace["paths"]["backups"])/"LK-BACKUP-CLI"; code,verified=_run(["backup-verify","--backup-directory",str(backup)],capsys); assert code==0; assert json.loads(created.out)==json.loads(verified.out)
def test_restore_command_restores_backup(tmp_path,capsys):
    root,workspace=_init(tmp_path,capsys); _run(["backup-create","--workspace-root",str(root),"--backup-id","LK-BACKUP-CLI","--created-at-utc","2026-08-18T20:00:00Z"],capsys); destination=tmp_path/"restored"; backup=Path(workspace["paths"]["backups"])/"LK-BACKUP-CLI"; code,captured=_run(["restore","--backup-directory",str(backup),"--destination-root",str(destination),"--restore-id","LK-RESTORE-CLI","--restored-at-utc","2026-08-18T20:10:00Z"],capsys); assert code==0; assert json.loads(captured.out)["status"]=="VERIFIED"
def test_operation_begin_inspect_and_list(tmp_path,capsys):
    root,_=_init(tmp_path,capsys); inputs=_json(tmp_path,"inputs.json",{"backup_id":"LK-BACKUP-1"}); base=["--workspace-root",str(root),"--operation-id","LK-OPERATION-CLI"]
    code,_=_run(["operation-begin",*base,"--operation-type","BACKUP","--actor","Founder","--occurred-at-utc","2026-08-18T20:00:00Z","--inputs-json-file",str(inputs)],capsys); assert code==0
    code,inspected=_run(["operation-inspect",*base],capsys); assert code==0; assert json.loads(inspected.out)["state"]=="STARTED"
    code,listed=_run(["operation-list","--workspace-root",str(root)],capsys); assert code==0; assert json.loads(listed.out)["operation_count"]==1
def test_checkpoint_and_resume_plan_are_non_executing(tmp_path,capsys):
    root,_=_init(tmp_path,capsys); inputs=_json(tmp_path,"inputs.json",{}); checkpoint=_json(tmp_path,"checkpoint.json",{"step":"VERIFIED"}); base=["--workspace-root",str(root),"--operation-id","LK-OPERATION-CLI"]
    _run(["operation-begin",*base,"--operation-type","INTEGRITY_AUDIT","--actor","Founder","--occurred-at-utc","2026-08-18T20:00:00Z","--inputs-json-file",str(inputs)],capsys)
    code,_=_run(["operation-checkpoint",*base,"--occurred-at-utc","2026-08-18T20:01:00Z","--checkpoint-json-file",str(checkpoint)],capsys); assert code==0
    code,planned=_run(["operation-resume-plan",*base],capsys); plan=json.loads(planned.out); assert code==0; assert plan["executes_operation"] is False
def test_complete_command_records_result(tmp_path,capsys):
    root,_=_init(tmp_path,capsys); inputs=_json(tmp_path,"inputs.json",{}); result=_json(tmp_path,"result.json",{"status":"PASS"}); base=["--workspace-root",str(root),"--operation-id","LK-OPERATION-CLI"]
    _run(["operation-begin",*base,"--operation-type","INTEGRITY_AUDIT","--actor","Founder","--occurred-at-utc","2026-08-18T20:00:00Z","--inputs-json-file",str(inputs)],capsys)
    code,captured=_run(["operation-complete",*base,"--occurred-at-utc","2026-08-18T20:01:00Z","--result-json-file",str(result)],capsys); assert code==0; assert json.loads(captured.out)["state"]=="COMPLETED"
def test_fail_command_records_error(tmp_path,capsys):
    root,_=_init(tmp_path,capsys); inputs=_json(tmp_path,"inputs.json",{}); base=["--workspace-root",str(root),"--operation-id","LK-OPERATION-CLI"]
    _run(["operation-begin",*base,"--operation-type","BACKUP","--actor","Founder","--occurred-at-utc","2026-08-18T20:00:00Z","--inputs-json-file",str(inputs)],capsys)
    code,captured=_run(["operation-fail",*base,"--occurred-at-utc","2026-08-18T20:01:00Z","--error","interrupted"],capsys); assert code==0; assert json.loads(captured.out)["error"]=="interrupted"
def test_invalid_json_file_returns_nonzero(tmp_path,capsys):
    root,_=_init(tmp_path,capsys); path=tmp_path/"bad.json"; path.write_text("not-json"); code,captured=_run(["operation-begin","--workspace-root",str(root),"--operation-id","LK-OPERATION-CLI","--operation-type","BACKUP","--actor","Founder","--occurred-at-utc","2026-08-18T20:00:00Z","--inputs-json-file",str(path)],capsys); assert code==2; assert captured.err.startswith("ERROR:")
def test_non_object_json_returns_nonzero(tmp_path,capsys):
    root,_=_init(tmp_path,capsys); path=_json(tmp_path,"array.json",[]); code,captured=_run(["operation-begin","--workspace-root",str(root),"--operation-id","LK-OPERATION-CLI","--operation-type","BACKUP","--actor","Founder","--occurred-at-utc","2026-08-18T20:00:00Z","--inputs-json-file",str(path)],capsys); assert code==2; assert "JSON object" in captured.err
def test_symlink_json_file_returns_nonzero(tmp_path,capsys):
    root,_=_init(tmp_path,capsys); target=_json(tmp_path,"target.json",{}); link=tmp_path/"link.json"; link.symlink_to(target); code,captured=_run(["operation-begin","--workspace-root",str(root),"--operation-id","LK-OPERATION-CLI","--operation-type","BACKUP","--actor","Founder","--occurred-at-utc","2026-08-18T20:00:00Z","--inputs-json-file",str(link)],capsys); assert code==2; assert "real JSON file" in captured.err
def test_operational_error_returns_nonzero(tmp_path,capsys):
    code,captured=_run(["audit","--workspace-root",str(tmp_path/"missing")],capsys); assert code==2; assert captured.out==""; assert captured.err.startswith("ERROR:")
def test_output_is_sorted_deterministic_json(tmp_path,capsys):
    root,_=_init(tmp_path,capsys); code,first=_run(["operation-list","--workspace-root",str(root)],capsys); code,second=_run(["operation-list","--workspace-root",str(root)],capsys); assert first.out==second.out; assert code==0
def test_cli_does_not_expose_publish_or_provider_commands():
    parser=cli.build_parser(); choices=next(action for action in parser._actions if isinstance(action,__import__("argparse")._SubParsersAction)).choices; assert all("publish" not in name and "wordpress" not in name and "provider" not in name for name in choices)

def test_release_certify_command_records_readiness(tmp_path,capsys):
    root,workspace=_init(tmp_path,capsys)
    inputs=_json(tmp_path,"release-inputs.json",{})
    result=_json(tmp_path,"release-result.json",{"status":"PASS"})
    base=["--workspace-root",str(root),"--operation-id","LK-OPERATION-RELEASE-CLI"]
    assert _run(["operation-begin",*base,"--operation-type","INTEGRITY_AUDIT","--actor","Founder","--occurred-at-utc","2026-08-18T22:00:00Z","--inputs-json-file",str(inputs)],capsys)[0]==0
    assert _run(["operation-complete",*base,"--occurred-at-utc","2026-08-18T22:01:00Z","--result-json-file",str(result)],capsys)[0]==0
    assert _run(["backup-create","--workspace-root",str(root),"--backup-id","LK-BACKUP-RELEASE-CLI","--created-at-utc","2026-08-18T22:02:00Z"],capsys)[0]==0
    backup=Path(workspace["paths"]["backups"])/"LK-BACKUP-RELEASE-CLI"
    code,captured=_run(["release-certify","--workspace-root",str(root),"--backup-directory",str(backup),"--release-id","LK-RELEASE-CLI","--certified-by","Founder","--certified-at-utc","2026-08-18T22:03:00Z","--source-commit","a"*40,"--required-operation-id","LK-OPERATION-RELEASE-CLI"],capsys)
    evidence=json.loads(captured.out)
    assert code==0
    assert evidence["status"]=="READY"
    assert evidence["public_launch_authorized"] is False
