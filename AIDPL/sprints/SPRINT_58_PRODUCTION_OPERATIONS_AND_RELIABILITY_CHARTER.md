# Sprint 58 — Production Operations and Reliability

## Status

`APPROVED — ACTIVE`

## Founder Approval

The Founder explicitly approved the Sprint 58 charter and the Phase 6/Phase 7
roadmap extension on 2026-08-18.

Repository synchronization is authorized. B2 discovery may begin after
synchronization. No implementation is authorized before B2 review.

## Roadmap Alignment

Sprint 58 begins:

`Phase 6 — Production Operations and Reliability`

Phase 7 remains reserved for final website and journal dressing and public
launch. Sprint 58 must not pull Phase 7 work forward.

## Starting Checkpoint

`24157ab` — `docs(aidpl): certify Sprint 57 editorial operations`

Inherited regression baseline:

`446 passed`

## Objective

Turn the certified LegalKural components into a reliable production operating
workflow without changing website or journal presentation.

An operator should be able to run, resume, audit, back up and restore the
governed pipeline using approved local paths and deterministic evidence.

## Core Principle

Operational convenience must not weaken governance, approval gates,
immutability, evidence lineage or fail-closed behavior.

## Scope

Sprint 58 should provide:

1. a standard production workspace contract;
2. an operator workflow spanning discovery, candidate preparation,
   finalization, build, verification and archival;
3. explicit checkpoints and safe resume after interruption;
4. idempotent rerun protection;
5. candidate and archive backup;
6. restore into an empty approved destination;
7. full candidate and archive integrity audit;
8. multi-article real-case operational validation;
9. configuration, secret and path-safety checks;
10. release versioning and an operator release package;
11. production-readiness certification and handover.

## Production Workspace

The workspace contract must separate:

- source/generated article evidence;
- candidate storage;
- finalized edition output;
- verified archive storage;
- backup storage;
- disposable runtime evidence;
- operator logs and certification summaries.

Paths must be caller-approved, explicit and inspectable.

## Operator Workflow

The workflow may orchestrate existing certified commands but must preserve
their separate state transitions and approval boundaries.

It must not silently:

- select articles;
- finalize a candidate;
- publish to WordPress;
- distribute a journal;
- overwrite an edition or archive entry;
- bypass verification.

## Resume and Idempotency

Interrupted operations must resume only from verified checkpoints.

Reruns must distinguish a safe no-op from a conflicting mutation. Partial,
ambiguous or hash-mismatched state must fail closed.

## Backup and Restore

Backup must preserve candidate revisions, finalization manifests, journal
artifacts, archive entries, hashes and canonical paths.

Restore must target an empty approved destination, verify all content before
acceptance and reject traversal, symlink, duplicate and tampered state.

No retention deletion policy is authorized.

## Integrity Audit

The audit must inspect the complete candidate and archive estate and report:

- object counts;
- revision-chain status;
- finalization status;
- artifact completeness;
- hash verification;
- canonical-path verification;
- duplicate identifiers;
- unexpected files;
- overall verdict.

The audit must not repair or delete data automatically.

## Real-Case Validation

The certified pilot may be used read-only. Additional real cases require
Founder-approved inputs and the existing legal, editorial and QA gates.

Synthetic fixtures must not be represented as published LegalKural articles.

## Security and Release Readiness

Sprint 58 must verify:

- no committed credentials or tokens;
- no secret values in runtime evidence;
- dependency inventory and reproducible environment instructions;
- path and symlink safety;
- least-authority operator instructions;
- deterministic release contents and checksums.

## Explicit Non-Goals

Sprint 58 does not include:

- website branding, theme or navigation;
- placeholder-site removal;
- final journal visual dressing;
- featured-image generation;
- public launch;
- email or social distribution;
- subscriptions, payments or analytics;
- provider calls during offline journal operations;
- WordPress writes without separate Founder authorization;
- deterministic Tamil generation;
- Tamil journal rendering;
- a graphical operator interface.

## Language and Kural Policy

Journal body rendering remains English-only.

Tamil rendering remains disabled.

The Thirukkural-inspired algorithm remains restricted to the article-title
contract.

## Initial Execution Boundary

B1 is Founder charter approval and repository synchronization only.

B2 must inspect the existing runtime, storage, resume, audit, backup, release,
configuration and security contracts before implementation architecture is
authorized.

No implementation is authorized before B2 discovery.

## Exit Criteria

Sprint 58 may close only when:

1. the production workspace contract is implemented;
2. the governed operator workflow is implemented;
3. checkpoint and resume behavior is deterministic;
4. rerun conflicts fail closed;
5. candidate and archive backup is implemented;
6. empty-destination restore is implemented and verified;
7. full integrity audit is implemented;
8. traversal, symlink, duplicate and tamper paths fail closed;
9. multi-article integration passes;
10. approved real-case operational validation passes;
11. secret and configuration safety checks pass;
12. the release package and checksums are deterministic;
13. provider and WordPress requests remain within explicit authorization;
14. Tamil rendering remains disabled;
15. title-only Kural policy is preserved;
16. regression does not fall below 446;
17. certification and operator handover are completed;
18. Founder closeout approval is recorded;
19. the repository closeout is remotely protected.

## Phase 7 Boundary

Phase 7 remains the final website and journal dressing and public-launch phase.
Sprint 58 must finish production operations and reliability first.
