# Model-Assisted QA Review v0.1

## Agent

`LK-QA-REVIEW`

## Purpose

Run an independent legal-fidelity audit after all specialist model reviews.

## Output

```text
evidence/qa-model-review-report.json
```

## Verdicts

```text
PASS
REVIEW_REQUIRED
FAIL
```

## Important Boundary

`PASS` does not publish the article.

It only opens the Founder review gate.

Publication still requires:

```text
QA review: PASS
Founder: AUTHORIZED
```

## Command

```bash
./bin/aidpl-review-qa \
  --case-id LK-OPENAI-PILOT-0001 \
  --case-root generated/LK-OPENAI-PILOT-0001 \
  --provider openai \
  --allow-live
```

## Next Action

```text
PASS            → FOUNDER_REVIEW
REVIEW_REQUIRED → REMEDIATION_REQUIRED
FAIL            → REMEDIATION_REQUIRED
```
