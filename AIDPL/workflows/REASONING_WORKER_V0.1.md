# Judicial Reasoning Worker v0.1

## Agent

`LK-REASON`

## Inputs

```text
working/source-text.txt
output/03-facts/facts.json
output/04-issues/issues.json
output/06-law/law.json
```

## Outputs

```text
output/07-reasoning/reasoning.json
output/08-decision/decision.json
evidence/reasoning-analysis-report.json
```

## Current Capability

- Reads structured facts, issues and law artifacts
- Detects judicial reasoning transitions
- Detects accepted and rejected argument candidates
- Detects ratio candidates
- Detects operative directions
- Detects case outcome
- Detects costs and limitations
- Preserves page-level traceability
- Validates reasoning and decision artifacts against schemas

## Boundary

Version 0.1 does not claim final legal interpretation.

The following still require model-assisted legal review:

- Final ratio decidendi
- Reliable accepted/rejected argument classification
- Complete relief mapping
- Distinction between holding and obiter
- Editorial explanation

## Orchestrator Effect

```text
LK-REASON → COMPLETE
LK-KURAL  → READY
```
