# Manual Task Governance v1.0

## Status

Certified runtime governance contract.

## Purpose

This workflow governs human/manual intervention inside the LegalKural
AIDPL execution lifecycle.

A manual task is a first-class persistent execution control.

An OPEN blocking manual task prevents protected agent execution until
the task is explicitly resolved.

## Core Lifecycle

The certified lifecycle is:

1. Runtime identifies a condition requiring human intervention.
2. A persistent manual task is created.
3. A blocking task enters OPEN state.
4. Protected agent execution is denied while the blocking task remains OPEN.
5. An authorized operator resolves the task through the manual-task
   operator surface.
6. Resolution is explicit:
   - COMPLETE; or
   - CANCEL.
7. Readiness is reconciled through the existing execution contract.
8. The execution gate is released when no OPEN blocking task remains.
9. Normal agent execution may safely re-enter through the existing
   orchestrator path.

## Persistence

Manual tasks are persisted as case evidence.

Task state must survive process boundaries and operator handoff.

The runtime must not depend on in-memory state alone for the existence
or resolution of a blocking manual task.

## Operator Surface

Manual tasks are managed through the certified manual-task CLI/runtime
surface.

Operator actions must be explicit and persisted.

A blocking task must not disappear merely because execution is retried.

## Execution Gate

The orchestrator owns the central execution gate.

Protected execution paths must respect the same manual-task blocking
contract.

Duplicating independent manual gates inside downstream workers is not
the intended architecture.

## Resolution

The certified terminal resolution states are:

- COMPLETE
- CANCEL

Both remove the OPEN blocking condition.

Resolution does not bypass ordinary readiness checks.

After resolution, the existing readiness contract determines whether
the next agent may execute.

## Safe Re-entry

No separate production-resume service is required.

No production-supervisor layer is required.

Safe re-entry is provided by the combination of:

- persistent manual-task state;
- explicit operator resolution;
- central execution gate;
- existing readiness reconciliation; and
- normal orchestrator execution.

## Failure Safety

An unresolved OPEN blocking task remains fail-closed.

Execution must not proceed merely because:

- the process restarted;
- the command was invoked again;
- another worker attempted execution; or
- an operator skipped the manual-task command.

## Publication Boundary

Manual-task resolution does not itself authorize publication.

Existing QA, founder authorization, publication and other human
governance gates remain independently authoritative.

## Provider Boundary

Manual-task governance does not itself authorize a model-provider
request.

Provider execution continues to require the applicable execution and
live-provider authorization contracts.

## Certified Implementation

Sprint 54 established:

- persistent manual-task detection;
- manual-task operator CLI;
- manual-task synchronization;
- central manual execution gate;
- enforcement across protected execution paths;
- COMPLETE -> gate release;
- CANCEL -> gate release;
- COMPLETE -> safe re-entry;
- CANCEL -> safe re-entry.

## Architectural Decision

The existing runtime contract is sufficient for safe re-entry.

A separate production-resume layer is not required.

A separate production-supervisor layer is not required.

## Governance Rule

Future execution entrypoints that can advance an AIDPL case must use
the certified central execution contract rather than implementing an
independent manual-task bypass or duplicate gate.
