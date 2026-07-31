# Judgment Intake Worker v0.1

## Agent

`LK-INTAKE`

## Purpose

Convert a judgment PDF into a verified and normalized source package.

## Outputs

```text
input/judgment.pdf
working/source-text.txt
working/page-map.json
evidence/source-integrity.json
evidence/source-integrity.txt
evidence/intake-report.json
manifest.json
```

## Validations

- File exists
- File is non-empty
- PDF signature is valid
- SHA-256 is calculated
- Page count is captured
- Embedded text is extracted page by page
- Every page receives a page boundary marker
- OCR requirement is detected when no text is available

## Orchestrator Effect

On success:

```text
LK-INTAKE  → COMPLETE
LK-EXTRACT → READY
```

The deterministic intake output is reviewed by the AI CEO.

Legal and editorial outputs remain subject to the independent QA gate.
