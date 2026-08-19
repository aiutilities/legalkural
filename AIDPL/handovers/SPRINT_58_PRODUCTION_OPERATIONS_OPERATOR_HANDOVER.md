# Sprint 58 — Production Operations and Reliability Operator Handover

## Status

`CERTIFIED — FOUNDER APPROVED`

## Purpose

This handover defines the offline production-operations sequence for a
LegalKural production workspace. It covers workspace initialization, audit,
append-only operation records, backup, restore and release-readiness evidence.

It does not authorize WordPress activity, publication, distribution, provider
requests or public launch.

## Certified Checkpoint

`a32474b8e58bd4e9a6707ef382a12de1a95b7266`

Run from the repository root:

```bash
export PYTHONPATH=engine
```

Use only explicit, caller-approved, non-symlinked local paths.

## Governed Sequence

### 1. Initialize

```bash
./bin/python -m operations.cli workspace-init \
  --workspace-root APPROVED_WORKSPACE_ROOT \
  --workspace-id WORKSPACE_ID
```

### 2. Audit

```bash
./bin/python -m operations.cli audit \
  --workspace-root APPROVED_WORKSPACE_ROOT
```

Proceed only when status is `PASS`. Audit never repairs or deletes content.

### 3. Record operations

```bash
./bin/python -m operations.cli operation-begin \
  --workspace-root APPROVED_WORKSPACE_ROOT \
  --operation-id OPERATION_ID \
  --operation-type INTEGRITY_AUDIT \
  --actor "Operator identity" \
  --occurred-at-utc YYYY-MM-DDTHH:MM:SSZ \
  --inputs-json-file INPUTS_JSON
```

Supported types are `INTEGRITY_AUDIT`, `BACKUP` and `RESTORE`. Events are
append-only and operation IDs must not be reused.

Use `operation-checkpoint`, `operation-complete` or `operation-fail` to record
the verified outcome. Use `operation-inspect`, `operation-list` and
`operation-resume-plan` for inspection. A resume plan is advisory and never
executes an operation.

### 4. Back up and verify

```bash
./bin/python -m operations.cli backup-create \
  --workspace-root APPROVED_WORKSPACE_ROOT \
  --backup-id BACKUP_ID \
  --created-at-utc YYYY-MM-DDTHH:MM:SSZ

./bin/python -m operations.cli backup-verify \
  --backup-directory APPROVED_WORKSPACE_ROOT/backups/BACKUP_ID
```

Do not overwrite, mutate, repair or delete a certified backup. No retention
deletion policy is authorized.

### 5. Restore and re-audit

```bash
./bin/python -m operations.cli restore \
  --backup-directory APPROVED_WORKSPACE_ROOT/backups/BACKUP_ID \
  --destination-root APPROVED_EMPTY_DESTINATION \
  --restore-id RESTORE_ID \
  --restored-at-utc YYYY-MM-DDTHH:MM:SSZ

./bin/python -m operations.cli audit \
  --workspace-root APPROVED_EMPTY_DESTINATION
```

Accept only a `VERIFIED` restore followed by a `PASS` audit with matching
workspace identity and backup evidence hash.

### 6. Certify release readiness

```bash
./bin/python -m operations.cli release-certify \
  --workspace-root APPROVED_WORKSPACE_ROOT \
  --backup-directory APPROVED_WORKSPACE_ROOT/backups/BACKUP_ID \
  --release-id RELEASE_ID \
  --certified-by "Certifier identity" \
  --certified-at-utc YYYY-MM-DDTHH:MM:SSZ \
  --source-commit FULL_40_CHARACTER_COMMIT \
  --required-operation-id OPERATION_ID
```

Repeat `--required-operation-id` as needed. Evidence is written under
`runtime-evidence/releases/RELEASE_ID/release-evidence.json`. Proceed only when
status is `READY`. Readiness does not authorize public launch.

## Stop Conditions

Stop on any symlink, traversal, unexpected file, duplicate identifier, hash
mismatch, tamper signal, incomplete required operation, prohibited secret file,
non-zero provider/WordPress request count, or failed audit/backup/restore.

Never commit OAuth data, credentials, tokens, private keys, `.env` files,
disposable runtime evidence or the local `generated/` tree.

## Preserved Boundaries

- Journal body remains English-only.
- Tamil rendering remains disabled.
- Thirukkural-inspired algorithm usage remains `TITLE_ONLY`.
- Sprint 57 continues to govern editorial and archive operations.
- WordPress activity requires separate Founder authorization.
- Website dressing and public launch remain Phase 7 work.

## Certification Summary

- Machine status: `SPRINT_58_B10_END_TO_END_VERIFIED`
- Regression: `555 passed`
- Provider requests: `0`
- WordPress requests: `0`
- Public launch authorized: `false`
