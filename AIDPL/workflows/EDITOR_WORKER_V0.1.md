# Legal Editorial Worker v0.1

## Agent

`LK-EDITOR`

## Inputs

All artifacts from metadata through Kural reasoning.

## Outputs

```text
output/10-article/article.md
evidence/editorial-report.json
```

## Current Capability

- Creates a structured article draft
- Includes case snapshot, story, law, evidence, reasoning and decision
- Explains the case for citizens, students and lawyers
- Preserves publication and legal-advice disclaimers
- Requires independent QA before publication

## Orchestrator Effect

```text
LK-EDITOR → COMPLETE
LK-QA     → READY
```
