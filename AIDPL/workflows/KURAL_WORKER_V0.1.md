# Kural Reasoning Worker v0.1

## Agent

`LK-KURAL`

## Inputs

```text
output/03-facts/facts.json
output/04-issues/issues.json
output/07-reasoning/reasoning.json
output/08-decision/decision.json
```

## Outputs

```text
output/09-kural/kural-brief.json
output/09-kural/kural.md
evidence/kural-generation-report.json
```

## Current Capability

- Derives an editorial brief from structured legal artifacts
- Separates legal holding from universal principle
- Produces a compressed title
- Produces an original English Kural-inspired line
- Preserves source traceability
- Includes a mandatory authenticity disclaimer
- Enforces human editorial review

## Safety Boundary

Version 0.1 intentionally does not generate Tamil verse.

Tamil Kural-inspired writing requires a human editor or a model-assisted
editorial stage with separate fidelity checks.

No generated writing may be represented as an authentic Thirukkural verse.

## Orchestrator Effect

```text
LK-KURAL  → COMPLETE
LK-EDITOR → READY
```
