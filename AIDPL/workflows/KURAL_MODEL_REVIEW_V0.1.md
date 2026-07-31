# Model-Assisted Kural Review v0.1

## Agent

`LK-KURAL-REVIEW`

## Outputs

```text
output/09-kural/kural-brief.json
output/09-kural/kural.md
evidence/kural-model-review-report.json
working/pre-kural-model-review/
```

## Commands

```bash
./bin/aidpl-review-kural \
  --case-id LK-OPENAI-PILOT-0001 \
  --case-root generated/LK-OPENAI-PILOT-0001 \
  --provider openai \
  --allow-live
```

Then:

```bash
./bin/aidpl-review-after-kural \
  --case-id LK-OPENAI-PILOT-0001 \
  --case-root generated/LK-OPENAI-PILOT-0001
```

## Mandatory Boundary

Generated Tamil and English writing is original Legal Kural editorial work.
It must never be represented as authentic Thirukkural.

Human Tamil and legal-fidelity review remain mandatory.

## Next Action

```text
MODEL_ASSISTED_EDITORIAL_REVIEW
```
