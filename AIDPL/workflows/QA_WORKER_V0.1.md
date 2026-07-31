# Legal Fidelity and QA Worker v0.1

## Agent

`LK-QA`

## Verdicts

- `PASS`
- `REVIEW_REQUIRED`
- `FAIL`

## Publication Rule

Agent completion does not automatically mean publication approval.

Publication requires:

```text
QA verdict: PASS
Founder: AUTHORIZED
```

A `REVIEW_REQUIRED` verdict permits LearningOS to run while publication
remains blocked.

## Output

```text
evidence/validation-report.json
```

## Orchestrator Effect

```text
LK-QA    → COMPLETE
LK-LEARN → READY
```
