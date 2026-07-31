# Model-Assisted Reasoning Review v0.1

## Agent

`LK-REASON-REVIEW`

## Outputs

```text
output/07-reasoning/reasoning.json
output/08-decision/decision.json
evidence/reasoning-model-review-report.json
working/pre-reasoning-model-review/
```

## Commands

```bash
./bin/aidpl-review-reason \
  --case-id LK-OPENAI-PILOT-0001 \
  --case-root generated/LK-OPENAI-PILOT-0001 \
  --provider openai \
  --allow-live
```

Then:

```bash
./bin/aidpl-review-after-reason \
  --case-id LK-OPENAI-PILOT-0001 \
  --case-root generated/LK-OPENAI-PILOT-0001
```

## Next Action

```text
MODEL_ASSISTED_KURAL_REVIEW
```
