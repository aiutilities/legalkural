# Phase 8 B2 — Public-Launch Preflight and Rollback Planning Boundary

## Status

`APPROVED — PLANNING ONLY`

## Starting checkpoint

`8b13c3ff14430c7341bf6c47d727e91c0574866e`

Phase 8 B1 closed as `CONDITIONALLY_READY`. Coming-soon protection and
discouraged indexing remain active. Public launch remains unauthorized.

## Objective

Produce an exact, reviewable preflight and rollback plan for a possible
future public launch. B2 converts the five B1 conditions into explicit checks,
success criteria, stop conditions, rollback actions and monitoring evidence.

## Exact repository boundary

B2 planning may modify only:

1. `AIDPL/design/PHASE_8_B2_PUBLIC_LAUNCH_PREFLIGHT_AND_ROLLBACK_PLAN.md`
2. `AIDPL/design/phase8/README.md`

No engine, schema, test, generated, credential or runtime file is in scope.

## Authorized discovery

B2 may use local repository reads and existing Phase 7 B9 / Phase 8 B1
evidence. If later separately authorized, a read-only preflight may perform
only documented `GET` requests and anonymous browser observations.

## Required planning output

The B2 plan must define:

1. exact checkpoint and expected WordPress site/post identities;
2. pre-launch anonymous desktop and physical-mobile evidence;
3. WordPress.com Free-plan presentation checks;
4. navigation and legal-route verification;
5. TITLE_ONLY post invariant and content hash verification;
6. coming-soon and indexing pre-state capture;
7. the single proposed launch mutation, without executing it;
8. a one-step rollback procedure to coming-soon protection;
9. critical and non-critical failure classifications;
10. post-launch monitoring checks and observation intervals;
11. request and mutation budgets;
12. the exact separate Founder authorization phrase required for execution.

## Launch decision matrix

| Gate | Pass condition | Failure action |
|---|---|---|
| Regression | `558 passed` | Stop |
| Repository | checkpoint exact; tracked tree clean | Stop |
| Visibility pre-state | coming-soon confirmed | Stop and investigate |
| Indexing pre-state | discouraged confirmed | Stop and investigate |
| Desktop/mobile | anonymous evidence accepted | Stop |
| Free-plan rendering | no visitor-facing premium dependency | Remove dependency or stop |
| Routes | navigation and legal routes resolve correctly | Stop |
| TITLE_ONLY | invariant and content hash pass | Stop |
| Rollback | restoration procedure independently reviewable | Stop |
| Founder approval | exact execution authorization received | Otherwise do not launch |

## Mandatory rollback design

The plan must preserve the full pre-state, name the exact reversal operation,
define verification after reversal and treat any critical homepage, article,
legal-route, mobile, TITLE_ONLY or HTTP failure as an immediate rollback
trigger. Rollback must not depend on repository edits or provider inference.

## Prohibited actions

B2 does not authorize:

- launching the site or removing coming-soon protection;
- changing `blog_public`, `robots.txt` behavior or search indexing;
- changing posts, pages, taxonomies, menus, templates, styles or navigation;
- buying or upgrading a WordPress plan;
- provider/model requests;
- staging, committing or pushing beyond the separately approved two-file
  documentation boundary;
- interpreting this planning approval as launch approval.

## Mutation and request budget

- WordPress requests during boundary implementation: `0`
- WordPress mutations: `0`
- Site Editor mutations: `0`
- Provider requests: `0`
- Public launch authorized: `NO`

## Completion gate

B2 planning is complete only after the exact two-file boundary passes
`git diff --check`, the complete regression remains `558 passed`, and the
Founder separately approves the resulting plan before any live preflight or
execution boundary is created.
