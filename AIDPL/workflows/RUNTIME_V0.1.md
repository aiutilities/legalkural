# AIDPL Runtime v0.1

## Purpose

Execute the complete Legal Kural deterministic pipeline with one command.

## Command

```bash
./bin/aidpl-run \
  path/to/judgment.pdf \
  --case-id LK-REF-0002
```

## Runtime Sequence

```text
ThinkingOS package initialization
        ↓
AIDPL plan initialization
        ↓
LK-INTAKE
        ↓
LK-EXTRACT
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

## Failure Rule

The runtime stops immediately when a worker fails.

## Publication Rule

A completed runtime does not imply publication approval.

Publication requires:

```text
QA verdict: PASS
Founder: AUTHORIZED
```

The deterministic v0.1 pipeline is expected to complete with:

```text
QA: REVIEW_REQUIRED
Next action: MODEL_ASSISTED_REVIEW
```

## Evidence

```text
evidence/runtime-report.json
```
