# Model-Assisted Editorial Review v0.1

## Agent

`LK-EDITOR-REVIEW`

## Outputs

```text
output/10-article/article.md
evidence/editorial-model-review-report.json
working/pre-editorial-model-review/10-article/article.md
```

## Commands

```bash
./bin/aidpl-review-editor \
  --case-id LK-OPENAI-PILOT-0001 \
  --case-root generated/LK-OPENAI-PILOT-0001 \
  --provider openai \
  --allow-live
```

Then:

```bash
./bin/aidpl-review-after-editor \
  --case-id LK-OPENAI-PILOT-0001 \
  --case-root generated/LK-OPENAI-PILOT-0001
```

## Next Action

```text
MODEL_ASSISTED_QA_REVIEW
```
