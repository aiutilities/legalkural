# Agent Self-Repair Contract v0.1

## Lifecycle

```text
GENERATE
   ↓
VALIDATE
   ↓
SCHEMA FAILURE
   ↓
SCHEMA CRITIC
   ↓
REPAIR WITHOUT NEW FACTS
   ↓
VALIDATE AGAIN
   ↓
PASS OR CONTROLLED FAILURE
```

## First Critic

`LK-LAW-SCHEMA-CRITIC`

The critic receives the invalid output, authoritative schema and exact
validation error. It may repair structure, but may not add legal substance.

## Safety

- Maximum two repair attempts.
- All initial validation errors are recorded.
- Failure after two attempts stops the worker.
- Founder approval and publication remain manual gates.
