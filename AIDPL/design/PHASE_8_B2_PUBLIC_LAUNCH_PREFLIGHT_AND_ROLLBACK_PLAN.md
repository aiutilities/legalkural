# Phase 8 B2 — Public-Launch Preflight and Rollback Plan

## Status

`DRAFT COMPLETE — FOUNDER REVIEW REQUIRED`

This document is a plan only. It does not authorize its preflight browser
session, its launch action, its rollback action or public indexing.

## Controlled identities

- Repository checkpoint: `9b78306eb533e8cc318159bf7f4931c388f521be`
- Site: `lkaidpl.wordpress.com`
- Pilot post ID: `10`
- Slug: `end-use-over-label-hostels-are-homes`
- Expected post state: `publish`
- TITLE_ONLY content SHA-256:
  `9d4493e8251da176d55e5547006d6bf1d46d734a901a44338f7c02fefef9fdce`
- Expected plan: `WordPress.com Free`
- Expected pre-launch visibility: `COMING_SOON`
- Expected pre-launch indexing: `DISCOURAGED` / `blog_public = 0`

## Separation of decisions

The site-visibility decision and search-indexing decision are deliberately
separated. The proposed launch makes the site anonymously reachable but keeps
indexing discouraged. Enabling indexing requires a later, separate Founder
authorization and is not part of B2.

## Stage A — machine and repository preflight

All checks are mandatory and fail closed:

1. `HEAD` and `origin/main` equal the authorized execution checkpoint.
2. The tracked working tree is clean.
3. `git diff --check` passes.
4. `PYTHONPATH=engine ./bin/python -m pytest -q engine/tests` reports
   `558 passed`.
5. No credential value is printed or copied into evidence.

## Stage B — read-only WordPress preflight

The separately authorized preflight may use only `GET` requests and anonymous
browser observations. It must record request method, response status, final
URL, byte count and SHA-256 without recording credentials.

Required observations:

1. authenticated site identity and WordPress.com Free plan;
2. settings showing coming-soon protection and `blog_public = 0`;
3. post 10 identity, publication state, slug and TITLE_ONLY content hash;
4. page inventory containing Judgments, Journal, Methodology, About, Privacy
   and Disclaimer;
5. anonymous homepage showing the coming-soon screen;
6. `robots.txt` consistent with discouraged indexing;
7. fresh anonymous desktop screenshots of homepage and post;
8. fresh anonymous physical-mobile screenshots of homepage and post;
9. navigation and every legal destination opened read-only;
10. no visible premium-style dependency or WordPress upgrade-only warning in
    the anonymous visitor presentation.

Any identity, TITLE_ONLY, legal-route, plan-rendering, regression or
visibility drift produces `NOT_READY` and stops execution.

## Stage C — Founder decision packet

The operator must present:

- the machine/read-only summary;
- accepted desktop and physical-mobile evidence;
- exact pre-state and evidence root;
- request count and confirmation of zero mutations;
- this launch action and rollback action;
- unresolved warnings, if any;
- a decision of `READY` or `NOT_READY`.

Only `READY` may proceed to a separate launch authorization.

## The single proposed launch mutation

After separate Founder authorization, the operator may perform exactly one
manual WordPress.com mutation:

> In the authenticated WordPress.com site administration for LegalKural,
> activate **Launch site** once, thereby removing Coming Soon protection.

The operator must not change content, menus, templates, styles, taxonomy,
plan, domain, `blog_public`, search visibility or any other setting in the
same execution. The action must stop if WordPress presents an upgrade,
domain, plan-selection or multi-setting workflow instead of a direct launch
confirmation.

## Immediate verification after launch

Within five minutes, using an anonymous session and a physical mobile device:

1. homepage returns the LegalKural homepage rather than Coming Soon;
2. post 10 loads and retains the approved TITLE_ONLY presentation;
3. all primary navigation and legal destinations resolve;
4. desktop and mobile layouts have no clipping, overlap or inaccessible text;
5. `robots.txt` and settings still reflect discouraged indexing;
6. no critical 4xx/5xx response is observed;
7. authenticated API identity and post hash remain unchanged.

## Immediate rollback triggers

Rollback is mandatory for any of these conditions:

- wrong site or unexpected public content;
- homepage or post unavailable;
- Tamil/literary section restored or TITLE_ONLY hash drift;
- missing Privacy or Disclaimer route;
- broken primary navigation;
- critical mobile clipping, overlap or unreadable content;
- indexing enabled without authorization;
- upgrade/paywall dependency affecting anonymous visitors;
- repeated HTTP 4xx/5xx responses;
- inability to complete verification within five minutes.

## One-step rollback action

Using the same authenticated WordPress.com site administration, restore the
site visibility to **Coming Soon** once. Do not combine rollback with any
other edit. If the direct Coming Soon control is unavailable, stop public
promotion immediately, preserve evidence and escalate; do not improvise an
API mutation.

After rollback, anonymously verify the Coming Soon screen, confirm indexing
remains discouraged, verify post/site identities through read-only requests,
and record the rollback result and request/mutation counts.

## Monitoring schedule

If launch verification passes:

| Time | Required checks |
|---|---|
| `T+5 min` | Full immediate verification set |
| `T+30 min` | Homepage, post, navigation, legal pages, HTTP status |
| `T+2 hr` | Desktop/mobile rendering, indexing and TITLE_ONLY |
| `T+24 hr` | Full validation set and incident review |
| Daily for 7 days | Availability, routes, indexing and post invariant |

Any critical failure during monitoring invokes the rollback contract.

## Budgets

- Planning implementation: `0` WordPress requests and `0` mutations.
- Read-only preflight: GET-only; exact count must be reported.
- Launch execution: exactly `1` WordPress mutation.
- Rollback, only if triggered: exactly `1` restoration mutation.
- Provider/model requests: `0`.
- Repository production-code changes: `0`.

## Required separate authorization phrases

Read-only preflight:

`Authorize Phase 8 B2 live read-only public-launch preflight at checkpoint <full-hash>`

Launch execution, only after a `READY` preflight:

`Authorize Phase 8 B2 single-mutation public launch at checkpoint <full-hash>`

Neither phrase is granted by approving or committing this plan.

## Current conclusion

`CONDITIONALLY_READY — PLAN COMPLETE; PREFLIGHT AND LAUNCH NOT AUTHORIZED`
