# Post-Certification Learning Runtime V1.0

## Purpose

The Post-Certification Learning Runtime allows LK-LEARN to perform
learning analysis after a LegalKural case has successfully completed
publication certification.

Learning is downstream of certification and must not rewrite,
invalidate, or silently alter the certified publication state.

## Preconditions

Post-certification learning may execute only when the certified QA
contract establishes:

- QA verdict is `PASS`.
- `publication_ready` is `true`.
- the certified workflow identifies `LK-LEARN` as the downstream agent.

If these conditions are not satisfied, the runtime must fail closed.

## Runtime

Canonical implementation:

`engine/aidpl/post_certification_learning_runtime.py`

The runtime prepares an isolated post-certification learning iteration
and invokes LK-LEARN against the certified case state.

The canonical semantic action is:

`POST_CERTIFICATION_LEARNING_REVIEW`

## Preservation Contract

Post-certification learning must preserve the substantive certified
state.

The following publication substance must remain unchanged:

- certified QA verdict;
- publication-ready state;
- publication contract;
- substantive outputs of non-learning agents;
- certified source and publication artifacts.

LK-LEARN may transition through its learning lifecycle without
rewriting the certified substantive state.

## Learning Output

The canonical learning result is recorded through the LearningOS
report contract.

The learning output records completion of the post-certification
review while retaining the certified QA/publication context.

Learning output is analytical evidence. It is not a replacement for
the certified publication artifact.

## Isolation

Certification testing must execute post-certification learning against
an isolated copy of a certified case.

The real certified pilot must remain unchanged.

## Provider Boundary

The runtime does not inherently require a provider request.

Provider execution, where separately authorized by another workflow,
must remain subject to the explicit provider and live-inference gates.

Sprint 52 certification required no provider request.

## Orchestrator Boundary

Sprint 52 introduced the post-certification runtime without modifying
the core orchestrator.

The runtime adapts the certified state for a legitimate downstream
learning iteration while preserving the existing orchestrator state
rules.

## Validation

Sprint 52 certification established:

- post-certification learning runtime: PASS;
- canonical learning output contract: PASS;
- certified substantive state preservation: PASS;
- real certified pilot unchanged: PASS;
- orchestrator core unchanged: PASS;
- full engine regression: 267 passed.

## Repository Boundary

Runtime evidence under `generated/` remains untracked and is not part
of the Sprint 52 source certification.

The unrelated Sprint 50 helper script is outside the Sprint 52 commit
boundary.
