# Downstream Review Runtime v0.1

## Purpose

Regenerate all downstream artifacts after model-assisted extraction review.

## Sequence

```text
Reviewed Metadata, Timeline, Facts, Issues and Evidence
        ↓
LK-LAW
        ↓
LK-REASON
        ↓
LK-KURAL
        ↓
LK-EDITOR
        ↓
LK-QA
        ↓
LK-LEARN
```

## Command

```bash
./bin/aidpl-review-run \
  --case-id LK-REF-0002 \
  --case-root generated/LK-REF-0002
```

## Behaviour

- Requires `extraction-model-review-report.json`.
- Preserves `LK-INTAKE` and `LK-EXTRACT` completion.
- Resets downstream agents.
- Clears the previous QA verdict.
- Executes six agents automatically.
- Stops on failure.
- Produces a new runtime evidence report.

## Evidence

```text
evidence/downstream-review-runtime-report.json
```

## Expected Deterministic Result

```text
QA: REVIEW_REQUIRED
Next action: MODEL_ASSISTED_LAW_REVIEW
```
