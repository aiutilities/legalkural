# Model-Assisted Extraction Review v0.1

## Agent

`LK-EXTRACT-REVIEW`

## Purpose

Review and consolidate the first five deterministic artifacts using the
configured model provider.

## Inputs

```text
working/source-text.txt
output/01-metadata/metadata.json
output/02-timeline/timeline.json
output/03-facts/facts.json
output/04-issues/issues.json
output/05-evidence/evidence.json
```

## Outputs

The five reviewed artifacts replace their deterministic drafts.

Original drafts are preserved under:

```text
working/pre-model-review/
```

Evidence is written to:

```text
evidence/extraction-model-review-report.json
```

## Safety

- Default provider is `mock`.
- Live inference requires `--allow-live`.
- Live providers require environment API keys.
- Output must validate against the existing five JSON schemas.
- The reviewer may not invent facts or silently remove uncertainty.

## Commands

Mock review:

```bash
./bin/aidpl-review-extract \
  --case-id LK-REF-0002 \
  --case-root generated/LK-REF-0002
```

Live review:

```bash
./bin/aidpl-review-extract \
  --case-id LK-REF-0002 \
  --case-root generated/LK-REF-0002 \
  --provider openai \
  --allow-live
```

## Next Action

After reviewed extraction artifacts are accepted, rerun:

```text
LK-LAW
LK-REASON
LK-KURAL
LK-EDITOR
LK-QA
LK-LEARN
```
