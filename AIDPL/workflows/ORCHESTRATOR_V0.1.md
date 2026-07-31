# AIDPL Orchestrator v0.1

## Purpose

The orchestrator is the AI CEO's machine-readable execution control.

It does not yet call AI models.

It currently governs:

- Agent sequence
- Dependencies
- Readiness
- Execution status
- Review separation
- Failure propagation
- QA gate
- Founder publication authorization
- Sprint status

## Commands

```bash
./bin/aidpl-orchestrator init \
  --case-id LK-REF-0002 \
  --case-root generated/LK-REF-0002 \
  --plan generated/LK-REF-0002/aidpl-plan.json
```

```bash
./bin/aidpl-orchestrator status \
  --plan generated/LK-REF-0002/aidpl-plan.json
```

```bash
./bin/aidpl-orchestrator start \
  --plan generated/LK-REF-0002/aidpl-plan.json \
  --agent LK-INTAKE
```

```bash
./bin/aidpl-orchestrator complete \
  --plan generated/LK-REF-0002/aidpl-plan.json \
  --agent LK-INTAKE \
  --reviewer LK-QA
```

## Constitutional Gate

No agent may review its own output.

Publication requires:

- `LK-QA: COMPLETE`
- `FOUNDER: AUTHORIZED`
