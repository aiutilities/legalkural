# Phase 8 B1 — Public-Launch Readiness Discovery Boundary

## Status

`APPROVED — READ-ONLY DISCOVERY ONLY — PUBLIC LAUNCH NOT AUTHORIZED`

## Founder approval

The Founder approved this exact B1 boundary after Phase 7 completion certification.

## Starting checkpoint

Phase 8 B1 starts from:

`a083fabb3df72ac8f7d5d02e7d0fa803202ff560`

This is the certified Phase 7 completion checkpoint. `HEAD` and `origin/main` must match it before B1 boundary implementation.

## Objective

Define a fail-closed, read-only discovery of everything required before a separate public-launch decision can be considered.

B1 may inspect and record facts. It may not change the website, repository production configuration, search visibility or public availability.

## Read-only discovery scope

The later B1 discovery execution may inspect:

1. current Coming Soon, privacy and public-visibility state;
2. current search-engine indexing setting;
3. active WordPress.com plan and plan-imposed visual limitations;
4. homepage, published judgment, navigation and footer rendering;
5. desktop and mobile layout, readability and overflow;
6. all header and footer destinations, including Judgments, Journal, Methodology, About, Privacy and Disclaimer;
7. published post status, canonical URL and taxonomy;
8. post-10 `TITLE_ONLY` compliance and absence of a Tamil/literary body block;
9. source-grounding, disclaimer and review-provenance presentation;
10. rollback, evidence capture and post-launch monitoring requirements;
11. exact Founder approvals needed for launch execution.

## Permitted operations

- local repository reads;
- read-only browser inspection of the existing site;
- read-only WordPress API requests when separately authorized for B1 execution;
- screenshots or machine-readable evidence written outside the repository;
- a later documentation-only evidence closeout under a separately approved exact boundary;
- the inherited automated regression suite.

## Prohibited operations

B1 does not authorize:

- clicking or invoking `Launch site`;
- disabling Coming Soon protection;
- enabling search-engine indexing;
- publishing, editing or deleting any page or post;
- changing categories, tags, author, slug, date or status;
- changing theme, templates, styles, typography, colours, layout or navigation;
- saving Site Editor changes;
- purchasing or upgrading a WordPress.com plan;
- provider requests;
- repository production-code changes;
- staging, committing or pushing discovery evidence without a separate approval;
- public-launch authorization or execution.

## Required evidence outputs

The B1 discovery result must state, without ambiguity:

- `READINESS_STATUS`: `READY`, `CONDITIONALLY_READY` or `NOT_READY`;
- `PUBLIC_LAUNCH_AUTHORIZED`: `NO`;
- current visibility and indexing states;
- plan name and confirmed limitations;
- desktop and mobile findings;
- navigation and legal-page findings;
- `TITLE_ONLY` findings;
- blockers and launch prerequisites;
- rollback and monitoring checklist;
- WordPress request count;
- WordPress mutation count, which must be `0`;
- Site Editor mutation count, which must be `0`.

## Fail-closed rules

The discovery must stop without mutation if authentication, API response shape, post identity, site identity, checkpoint, visibility state or expected evidence drifts.

Unknown or unverifiable facts must be reported as blockers. They must not be guessed.

## Regression baseline

Inherited repository regression baseline:

`558 passed`

## Exit condition

B1 is complete only after its read-only findings are reviewed and a separate evidence-closeout boundary is approved.

Completion of B1 does not authorize B2 or public launch.
