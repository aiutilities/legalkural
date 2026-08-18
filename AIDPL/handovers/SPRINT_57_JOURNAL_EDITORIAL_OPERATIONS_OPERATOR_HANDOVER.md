# Sprint 57 — Journal Editorial Operations Operator Handover

## Status

`CERTIFIED — FOUNDER APPROVED`

## Purpose

This handover defines the offline operator sequence for preparing,
finalizing, building, verifying and archiving a LegalKural journal edition.
It does not authorize WordPress activity or journal distribution.

## Governed Sequence

Keep discovery, candidate editing, inspection, finalization, building,
verification, archival and archive verification as separate actions.

A candidate is not final. A finalized candidate cannot be revised.

Run from the repository root with:

```bash
export PYTHONPATH=engine
```

Use only caller-approved local candidate, edition and archive paths.

## Discover

```bash
./bin/python -m journal.cli discover --generated-root generated
```

Review eligible and rejected articles before selection.

## Create Candidate

```bash
./bin/python -m journal.cli candidate-create \
  --storage-root CANDIDATE_ROOT \
  --candidate-id CANDIDATE_ID \
  --generated-root generated \
  --journal-id JOURNAL_ID \
  --edition-date YYYY-MM-DD \
  --title "Journal title" \
  --editor "Editor identity" \
  --revised-at-utc YYYY-MM-DDTHH:MM:SSZ \
  --case-id CASE_ID
```

Repeat `--case-id` in the intended editorial order.

## Inspect and Revise

```bash
./bin/python -m journal.cli candidate-inspect \
  --storage-root CANDIDATE_ROOT --candidate-id CANDIDATE_ID

./bin/python -m journal.cli candidate-list \
  --storage-root CANDIDATE_ROOT --candidate-id CANDIDATE_ID

./bin/python -m journal.cli candidate-revise \
  --storage-root CANDIDATE_ROOT \
  --candidate-id CANDIDATE_ID \
  --generated-root generated \
  --revised-at-utc YYYY-MM-DDTHH:MM:SSZ \
  --case-id FIRST_CASE_ID --case-id SECOND_CASE_ID
```

Each revision contains the complete desired ordered selection. Reorder by
changing argument order, remove by omission and add only eligible case IDs.
Earlier revisions remain immutable.

## Finalize, Build and Verify

```bash
./bin/python -m journal.cli candidate-finalize \
  --storage-root CANDIDATE_ROOT \
  --candidate-id CANDIDATE_ID \
  --generated-root generated \
  --selected-by "Approver identity" \
  --finalized-at-utc YYYY-MM-DDTHH:MM:SSZ

./bin/python -m journal.cli candidate-build \
  --project-root . \
  --storage-root CANDIDATE_ROOT \
  --output-root EDITION_ROOT \
  --candidate-id CANDIDATE_ID

./bin/python -m journal.cli verify \
  --edition-directory EDITION_ROOT/JOURNAL_ID
```

Proceed only when the build is `COMPLETE`, verification is `VERIFIED`, and
provider and WordPress request counts are zero.

## Archive and Reverify

```bash
./bin/python -m journal.cli archive-register \
  --archive-root ARCHIVE_ROOT \
  --edition-directory EDITION_ROOT/JOURNAL_ID \
  --archived-at-utc YYYY-MM-DDTHH:MM:SSZ

./bin/python -m journal.cli archive-list --archive-root ARCHIVE_ROOT

./bin/python -m journal.cli archive-inspect \
  --archive-root ARCHIVE_ROOT --journal-id JOURNAL_ID

./bin/python -m journal.cli archive-verify \
  --archive-root ARCHIVE_ROOT --journal-id JOURNAL_ID
```

Final archive verification must be `VERIFIED`.

## Stop Conditions

Stop without bypassing validation if an article is rejected, a hash or path
mismatch appears, finalization fails, a build is incomplete, a request count
is non-zero, verification fails, or a symlink/traversal error appears.

Never overwrite revisions, finalized artifacts or archive entries.

## Product Boundaries

- Journal body remains English-only.
- Tamil rendering remains disabled.
- Thirukkural-inspired algorithm usage remains title-only.
- WordPress publishing and journal distribution require separate approval.
- Website and journal visual dressing remain deferred to the final sprint.
