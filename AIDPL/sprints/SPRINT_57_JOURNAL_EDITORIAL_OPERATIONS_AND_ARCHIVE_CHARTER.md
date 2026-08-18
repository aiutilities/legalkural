# Sprint 57 — Journal Editorial Operations and Archive

## Status

`APPROVED — ACTIVE`

## Founder Approval

The Sprint 57 charter was explicitly approved by the Founder on
2026-08-18.

Repository synchronization is authorized. Implementation remains
subject to the B2 discovery boundary defined below.

## Roadmap Alignment

Sprint 57 continues:

`Phase 5 — Weekly Journal Generation`

The repository roadmap currently ends at Phase 5. Sprint 57 completes
the operational layer around the certified Sprint 56 journal-generation
foundation. It does not create or assume a Phase 6.

## Starting Checkpoint

Sprint 57 starts from:

`69dd4d7` — `docs(aidpl): certify Sprint 56 weekly journal foundation`

Sprint 56 is closed, Founder-approved, certified and remotely
protected.

Inherited regression baseline:

`373 passed`

## Objective

Add a governed editorial candidate lifecycle and durable local journal
archive around the certified journal builder.

An editor must be able to create and revise a candidate edition, review
its contents and ordering, deliberately finalize it, build the journal,
store the completed edition in a deterministic archive and inspect or
verify archived editions.

## Core Principle

Discovery, candidate editing, manifest finalization, PDF generation and
archival are separate governed actions.

Creating or editing a candidate must never silently finalize, build,
publish or distribute an edition.

## Candidate Lifecycle

The lifecycle is:

1. discover eligible certified articles;
2. explicitly select articles;
3. create a candidate edition;
4. inspect the candidate;
5. reorder or remove selected articles;
6. record a new append-only candidate revision;
7. review the proposed final order;
8. deliberately finalize the candidate;
9. generate the immutable manifest and journal;
10. register the verified edition in the local archive.

Required states:

- `CANDIDATE`
- `FINALIZED`
- `BUILT`
- `VERIFIED`
- `ARCHIVED`

Invalid state transitions must fail closed.

## Candidate Contract

A candidate must preserve:

- schema version;
- candidate ID;
- revision number;
- previous revision hash where applicable;
- journal ID;
- edition date;
- proposed title;
- editor identity;
- creation timestamp;
- last-revision timestamp;
- ordered selected case IDs;
- selected publication evidence and source hashes;
- candidate status;
- candidate SHA-256.

Candidate revision history must be append-only.

A prior revision must not be silently overwritten.

## Editorial Operations

The offline CLI foundation should support:

- create candidate;
- inspect candidate;
- list candidate revisions;
- reorder selected articles;
- remove an article;
- add an eligible article;
- create a new revision;
- finalize deliberately;
- reject duplicate selected case IDs;
- reject ineligible additions;
- reject edits after finalization.

The exact command names may be fixed during implementation discovery.

## Finalization Boundary

Finalization must:

- require an existing valid candidate revision;
- require at least one eligible selected article;
- preserve the recorded editorial order;
- revalidate source and publication hashes;
- produce the Sprint 56 immutable manifest contract;
- record the candidate identity and revision lineage;
- prevent further mutation of the finalized revision.

A changed selection must create a new candidate or revision.

## Archive Contract

The local archive must provide deterministic storage for completed,
verified journal editions.

The archive must preserve:

- archive schema version;
- journal ID;
- edition date;
- covered publication-date range;
- article count;
- selected case IDs;
- manifest SHA-256;
- assembly SHA-256;
- PDF SHA-256;
- renderer version;
- verification status;
- archive timestamp;
- canonical relative paths;
- archive-entry SHA-256.

The archive must support:

- register a verified edition;
- list archived editions;
- inspect an archive entry;
- verify an archived edition;
- reject duplicate journal IDs;
- reject hash or path mismatches;
- reject incomplete or unverified editions.

## Storage Safety

Sprint 57 must:

- use caller-approved local paths;
- avoid hidden external storage;
- use atomic writes and directory moves;
- prevent path traversal and symlink escapes;
- preserve immutable completed editions;
- avoid destructive overwrite;
- fail closed on partial archive state;
- leave runtime evidence untracked unless separately authorized.

No retention deletion policy is authorized in this sprint.

## Real Pilot Boundary

The certified article:

`LK-OPENAI-PILOT-0001`

may be used for read-only discovery and disposable local integration
testing.

Sprint 57 must not:

- modify WordPress post ID 10;
- create a new WordPress post;
- update WordPress taxonomy;
- perform a provider request;
- distribute a journal publicly.

## Test Strategy

Synthetic fixtures must prove:

- candidate creation;
- explicit selection;
- candidate inspection;
- reorder operation;
- article removal;
- eligible article addition;
- append-only revisions;
- revision hash chaining;
- invalid revision rejection;
- edit-after-finalization rejection;
- deliberate finalization;
- manifest lineage to candidate revision;
- atomic archive registration;
- deterministic archive index;
- duplicate archive rejection;
- incomplete-edition rejection;
- tampered-edition rejection;
- path and symlink rejection;
- archived-edition verification.

Synthetic fixtures must not be represented as published LegalKural
articles.

## Explicit Non-Goals

Sprint 57 does not include:

- website branding or navigation;
- WordPress theme changes;
- placeholder website removal;
- anonymous website launch;
- final PDF visual dressing;
- featured-image generation;
- email delivery;
- social sharing;
- subscriptions;
- payments;
- analytics;
- external print fulfilment;
- journal distribution;
- provider calls;
- WordPress writes;
- deterministic Tamil generation;
- Tamil journal rendering;
- regeneration of certified legal analysis;
- a graphical editorial interface.

## Language and Kural Policy

Journal body rendering remains English-only.

Tamil rendering remains disabled.

The Thirukkural-inspired algorithm remains restricted to the article
title contract.

## Initial Execution Boundary

B1 is charter approval and repository synchronization only.

B2 must inspect existing storage, document-store, archive, manifest,
workflow and CLI contracts before implementation.

No implementation architecture is authorized before B2 discovery.

## Exit Criteria

Sprint 57 may close only when:

1. candidate schema and validation are implemented;
2. explicit candidate creation is implemented;
3. editorial reorder, add and remove operations are implemented;
4. append-only revision history is implemented;
5. invalid state transitions fail closed;
6. deliberate candidate finalization is implemented;
7. candidate-to-manifest lineage is preserved;
8. production archive schema is implemented;
9. atomic archive registration is implemented;
10. archive list, inspect and verify operations are implemented;
11. duplicate and tamper paths fail closed;
12. synthetic multi-article integration passes;
13. certified-pilot read-only integration passes;
14. provider and WordPress requests remain zero;
15. the full regression does not regress below 373;
16. certification and operator handover are completed;
17. Founder closeout approval is recorded;
18. the repository closeout is remotely protected.

## Deferred Final Sprint

Website and journal visual dressing remain reserved for the final
website-dressing sprint.

Sprint 57 must not pull that work forward.
