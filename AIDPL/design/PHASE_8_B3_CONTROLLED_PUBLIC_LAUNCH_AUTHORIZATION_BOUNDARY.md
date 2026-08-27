# Phase 8 B3 — Controlled Public-Launch Authorization Boundary

## Status

DEFINED — NOT AUTHORIZED

This document defines the exact authorization and execution boundary for a future controlled public launch. Creating or committing this document does not authorize, perform, or simulate a WordPress.com mutation.

## Source checkpoint and lineage

- Approved source checkpoint: `e7fc998f2ca557c104bd1346ab67d6a11790de31`.
- Phase 8 B2 live read-only public-launch preflight evidence is closed at that checkpoint.
- Expected repository regression baseline: 558 passing tests.
- The current public state remains `COMING_SOON`.

## Sole permitted launch mutation

If the Founder later gives a separate, checkpoint-specific execution authorization, the sole permitted live mutation is the WordPress.com site visibility/launch transition from `COMING_SOON` to `PUBLIC` (launched).

The authorization does not permit changes to content, posts, titles, slugs, categories, tags, authors, publication dates, domains, plans, purchases, themes, styles, templates, navigation, footer, palette, typography, layout, search-engine indexing preferences, or any other setting.

The pilot post remains immutable. `TITLE_ONLY` remains the governing Thirukkural mode. No provider inference or editorial regeneration is authorized.

## Required pre-mutation gates

All gates must pass immediately before any live launch action:

1. `HEAD` and `origin/main` equal the separately authorized checkpoint.
2. The complete regression suite reports 558 passing tests.
3. The tracked worktree is clean and unrelated untracked paths are unchanged.
4. The authenticated WordPress.com identity and target site are verified.
5. The authenticated pre-state is captured and shows `COMING_SOON`.
6. Anonymous desktop Private browsing and anonymous mobile browsing show the WordPress.com coming-soon screen.
7. Search-engine indexing remains discouraged and must not be changed by this operation.
8. The exact rollback route is identified and available.
9. The Founder supplies an explicit launch-execution authorization naming the checkpoint.
10. Any screen, control, wording, site identity, or state that differs from the evidence causes an immediate stop.

## Controlled execution boundary

A later authorized operator may perform one visibility/launch action only. The operator must not accept an upgrade, buy or select a plan or domain, change indexing, edit site content or design, or continue through an unexpected prompt. A materially different interface or ambiguous effect is a stop condition.

## Immediate verification gates

After the single action, execution is incomplete until all applicable checks pass:

- Authenticated WordPress.com state identifies the correct LegalKural site as public/launched.
- Anonymous desktop Private browsing displays the LegalKural home page, not the coming-soon or sign-in screen.
- Anonymous mobile browsing displays the LegalKural site, not the coming-soon or sign-in screen.
- Home, navigation routes, footer links, and the published pilot post remain reachable.
- Anonymous views contain no administrative toolbar.
- Desktop and mobile layouts remain readable and operational.
- Pilot title, slug, content, author, date, categories, tags, and publication lineage remain unchanged.
- `TITLE_ONLY` remains intact and no removed literary section reappears.
- Search-engine indexing remains discouraged.
- Every WordPress request and mutation is counted and reported; no unapproved mutation is present.

## Rollback triggers and boundary

Rollback consideration is mandatory if visibility is unexpected, an anonymous view produces a redirect, 404, sign-in wall, or coming-soon screen, content or metadata drifts, navigation fails, layout becomes unusable, indexing changes, an unexpected request or mutation occurs, verification cannot be completed, or a plan/domain/upgrade prompt obstructs the approved action.

The rollback target is restoration of `COMING_SOON`. Existing governance is preserved: rollback execution requires separate explicit Founder authorization unless the later checkpoint-specific launch authorization expressly includes a narrowly defined safety rollback. No automatic rollback mutation is authorized by this boundary.

## Stop points

Stop before mutation if any precondition fails. Stop after the one permitted action; do not make corrective edits. Stop and report if any verification gate fails. Do not repeat the launch control, alter unrelated settings, or improvise around WordPress.com prompts.

## Required evidence closeout

A separate evidence-closeout boundary must record checkpoint identity, pre-state, authorization text, timestamps, authenticated and anonymous verification, desktop and mobile evidence, request and mutation counts, post-state, rollback status, regression result, and repository integrity. That closeout requires a separate exact-boundary approval before repository changes.

## Authorization ledger

- Public launch authorized: **NO**
- Public launch performed: **NO**
- Rollback authorized: **NO**
- Rollback performed: **NO**
- WordPress requests for this boundary implementation: **0**
- WordPress mutations for this boundary implementation: **0**
- Site Editor mutations for this boundary implementation: **0**

PHASE 8 B3 CONTROLLED PUBLIC-LAUNCH AUTHORIZATION BOUNDARY: PASS
