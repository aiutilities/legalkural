# Legal Extraction Worker v0.1

## Agent

`LK-EXTRACT`

## Inputs

```text
working/source-text.txt
working/page-map.json
```

## Outputs

```text
output/01-metadata/metadata.json
output/02-timeline/timeline.json
output/03-facts/facts.json
output/04-issues/issues.json
output/05-evidence/evidence.json
evidence/extraction-report.json
```

## Current Capability

Version 0.1 performs deterministic extraction and schema validation.

It can:

- Detect court, judge, case numbers and decision dates
- Detect dated timeline candidates
- Detect candidate factual statements
- Detect issue formulations
- Detect documentary, electronic and missing-evidence candidates
- Preserve page traceability
- Validate all five artifacts against JSON schemas

## Boundary

This version does not claim complete legal understanding.

Facts, allegations, issues and evidence still require model-assisted legal review.

## Orchestrator Effect

On successful deterministic extraction:

```text
LK-EXTRACT → COMPLETE
LK-LAW     → READY
```
