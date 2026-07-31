# Legal Analysis Worker v0.1

## Agent

`LK-LAW`

## Input

```text
working/source-text.txt
output/03-facts/facts.json
output/04-issues/issues.json
```

Version 0.1 directly reads normalized source text. Facts and issues become formal worker inputs in the model-assisted version.

## Outputs

```text
output/06-law/law.json
evidence/law-analysis-report.json
```

## Current Capability

- Detect constitutional provisions
- Detect statutes and sections
- Detect regulations
- Detect notifications
- Detect reported case citations
- Detect legal doctrines
- Detect ratio candidates
- Preserve page traceability
- Validate output against JSON Schema

## Boundary

Version 0.1 does not independently determine:

- Binding authority
- Correct citation normalization
- Whether a precedent was followed, distinguished or rejected
- Final ratio decidendi
- Obiter dicta

These require model-assisted legal review.

## Orchestrator Effect

```text
LK-LAW    → COMPLETE
LK-REASON → READY
```
