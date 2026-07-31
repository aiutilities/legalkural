# Model-Assisted Law Review v0.1

## Agent

`LK-LAW-REVIEW`

## Outputs

```text
output/06-law/law.json
evidence/law-model-review-report.json
working/pre-law-model-review/06-law/law.json
```

## Commands

```bash
./bin/aidpl-review-law \
  --case-id LK-OPENAI-PILOT-0001 \
  --case-root generated/LK-OPENAI-PILOT-0001 \
  --provider openai \
  --allow-live
```

Then regenerate downstream artifacts without overwriting the reviewed law:

```bash
./bin/aidpl-review-after-law \
  --case-id LK-OPENAI-PILOT-0001 \
  --case-root generated/LK-OPENAI-PILOT-0001
```

## Next Action

```text
MODEL_ASSISTED_REASONING_REVIEW
```
