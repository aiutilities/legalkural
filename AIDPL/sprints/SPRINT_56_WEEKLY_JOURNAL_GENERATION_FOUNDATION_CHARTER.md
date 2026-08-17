# Sprint 56 — Weekly Journal Generation Foundation

## Status

PROPOSED / IMPLEMENTATION NOT STARTED

## Founder Approval

Approved objective:

Build an offline-first, deterministic, editor-selected, print-ready
weekly journal workflow.

Explicit exclusions:

- website dressing;
- WordPress writes;
- journal distribution;
- Anthropic support;
- deterministic Tamil generation.

## Roadmap Alignment

Sprint 56 implements the foundation for:

`Phase 5 — Weekly Journal Generation`

The preceding roadmap phase, WordPress Publishing, was certified and
closed in Sprint 55.

## Starting Checkpoint

Sprint 56 starts from:

`ba0794a` — `docs(aidpl): certify Sprint 55 production pilot`

Sprint 55 is closed, certified and remotely protected.

## Objective

Build and certify the offline foundation required to assemble selected
published LegalKural articles into a reproducible, print-ready weekly
journal PDF.

The sprint must use certified article outputs and publication evidence.

It must not regenerate or reinterpret the underlying legal analysis.

## Core Principle

A weekly journal is a governed compilation artifact.

It must preserve the identity, provenance and certified meaning of its
source articles while providing deterministic editorial selection,
ordering, layout and evidence.

## Initial Workflow

The intended workflow is:

1. discover eligible certified articles;
2. present article candidates for editorial selection;
3. record an explicit selection;
4. create an immutable edition manifest;
5. validate source identities and hashes;
6. order and group articles deterministically;
7. create a journal preview;
8. render a print-ready PDF;
9. validate the generated PDF;
10. create journal-generation evidence;
11. require separate certification before any distribution.

## Offline-First Boundary

Sprint 56 must operate offline against local certified artifacts and
fixtures.

The sprint must not require:

- a WordPress write;
- a WordPress draft;
- a new WordPress publication;
- a provider request;
- email delivery;
- social distribution;
- website launch.

Read-only inspection of preserved publication evidence is permitted.

## Source Eligibility

An article may be eligible only when the journal workflow can verify,
as applicable:

- stable case identity;
- certified article identity;
- article title;
- publication status evidence;
- publication URL;
- publication date;
- category and tags;
- author;
- certified or approved content hash;
- required review and QA state;
- publication evidence identity.

An unverifiable source must fail closed.

## Editor Selection

Selection must be explicit.

The editor must be able to:

- view eligible candidates;
- select one or more articles;
- define or confirm edition order;
- remove an article before manifest finalization;
- review the proposed edition;
- finalize the selection deliberately.

Discovery alone must not create a finalized journal edition.

## Edition Identity

Every journal edition must have a deterministic identity derived from
controlled inputs such as:

- journal name;
- edition period;
- edition sequence or stable identifier;
- finalized article identities;
- finalized article order;
- source content hashes;
- manifest schema version.

The system must prevent accidental duplicate editions for the same
finalized identity.

## Immutable Manifest

The finalized edition manifest must preserve:

- schema version;
- journal edition ID;
- edition title;
- covered date range;
- creation timestamp;
- article count;
- ordered article entries;
- source case IDs;
- source article titles;
- source publication URLs;
- source publication dates;
- categories and tags;
- source content hashes;
- manifest hash;
- workflow status.

A finalized manifest must not be silently mutated.

Changes must create a new candidate or revision under an explicit
contract.

## Deterministic Ordering

Given the same finalized manifest and renderer version, article order
and document structure must be reproducible.

Default ordering must be explicit and testable.

Manual editorial ordering, when used, must be recorded in the
manifest.

## Journal Structure

The foundation should support:

- cover page;
- journal title;
- edition date or date range;
- contents page;
- ordered article sections;
- article title and metadata;
- original LegalKural passage where present;
- source/publication reference;
- editorial disclaimer;
- page numbering;
- closing publication information.

The exact visual brand is not part of this sprint.

## PDF Requirement

The output must be a print-ready PDF suitable for later human review.

The PDF contract should validate at least:

- file exists and is non-empty;
- valid PDF structure;
- expected page count;
- expected edition title;
- expected article count;
- expected ordered article titles;
- no missing article sections;
- no unexpected blank pages;
- reproducible generation from the same manifest;
- recorded PDF SHA-256.

## Pilot and Test Strategy

The first real fixture is the certified Sprint 55 article:

`LK-OPENAI-PILOT-0001`

`End-Use Over Label: Hostels Are Homes`

The one-article fixture proves integration with preserved certified
evidence.

Synthetic fixtures must be used to prove:

- multiple eligible articles;
- editor selection;
- deterministic ordering;
- duplicate prevention;
- source-hash mismatch rejection;
- missing evidence rejection;
- invalid date-range rejection;
- manifest finalization;
- PDF structure;
- repeatable output.

Synthetic fixtures must not be mistaken for published LegalKural
articles.

## Evidence Requirement

The sprint must produce sufficient evidence to reconstruct:

- candidate discovery;
- editor selection;
- source validation;
- manifest creation;
- manifest finalization;
- edition identity;
- renderer version;
- PDF generation;
- PDF validation;
- source hashes;
- manifest hash;
- PDF hash;
- duplicate checks;
- failures and recovery where applicable.

## Safety Requirements

The implementation must preserve:

- Sprint 55 publication evidence;
- source-document immutability;
- certified article content;
- existing provider gates;
- existing manual-task governance;
- existing QA and Founder authorization boundaries;
- WordPress publication state;
- untracked runtime-evidence policy.

## Explicit Non-Goals

Sprint 56 does not include:

- LegalKural website branding;
- WordPress theme or navigation changes;
- removal of placeholder website content;
- anonymous WordPress site launch;
- WordPress article creation or modification;
- featured-image generation;
- journal email delivery;
- journal social sharing;
- subscriptions;
- payment or membership;
- analytics;
- external print fulfillment;
- Anthropic provider support;
- deterministic Tamil Kural generation;
- regeneration of certified legal analysis;
- a new supervisor or resume architecture.

## Initial Execution Boundary

B1 is charter and repository-direction synchronization only.

B2 must inspect existing article, archive, PDF and journal-related
contracts before implementation.

No implementation architecture is authorized until discovery confirms
what can be reused.

## Exit Criteria

Sprint 56 may close only when:

1. eligible-source discovery is implemented and tested;
2. explicit editor selection is implemented and tested;
3. deterministic edition identity is implemented and tested;
4. immutable manifest generation is implemented and tested;
5. duplicate prevention is implemented and tested;
6. one-article certified-pilot integration passes;
7. multi-article synthetic integration passes;
8. print-ready PDF generation passes;
9. PDF validation passes;
10. evidence and hashes are preserved;
11. failure paths fail closed;
12. the full engine regression does not regress;
13. certification and handover are completed;
14. repository closeout is Founder-approved and remotely protected.

## Baseline Regression

Sprint 56 inherits the Sprint 55 baseline:

`324 passed`

This baseline must not regress.

## Deferred Final Website Sprint

Website dressing and anonymous WordPress site launch remain reserved
for the final website-dressing sprint.

Sprint 56 must not pull that work forward.
