# Autonomous Remediation Runtime v0.1

## Agent

`LK-REMEDIATION`

## Objective

Teach the Legal Kural agents to correct their own QA findings.

## Loop

```text
OpenAI QA
   ↓
LK-REMEDIATION
   ↓
Classify findings
   ↓
Assign owning agents
   ↓
Rerun from earliest affected stage
   ↓
OpenAI QA again
   ↓
PASS or controlled stop
```

## Safety Boundaries

- Default provider is `mock`.
- Live remediation requires `--allow-live`.
- Maximum iterations are restricted to three.
- Founder authorization is never granted automatically.
- Publication remains false even when QA returns PASS.
- A non-converging case is escalated for human exception review.

## Command

```bash
./bin/aidpl-remediate \
  --case-id LK-OPENAI-PILOT-0001 \
  --case-root generated/LK-OPENAI-PILOT-0001 \
  --provider openai \
  --allow-live \
  --max-iterations 1
```

## Evidence

```text
evidence/remediation-plan-001.json
evidence/remediation-iteration-001.json
evidence/remediation-runtime-report.json
```
