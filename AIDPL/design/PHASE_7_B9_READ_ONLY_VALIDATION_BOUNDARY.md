# Phase 7 B9 — Read-Only Validation Boundary

## Status

`FOUNDER APPROVED — READ-ONLY BOUNDARY`

## Authorization

The Founder approved this exact boundary after the Phase 7 B8 manual visual
execution closed as
`EXECUTED_NO_MUTATION_BLOCKED_BY_PLAN_LIMITATIONS` at checkpoint `a5cf0c3`.

This boundary authorizes inspection and evidence capture only. It authorizes no
WordPress mutation, repository implementation beyond B9 evidence, publication,
indexing change, Coming Soon removal or public launch.

## Objective

Evaluate the present pilot baseline against the approved Phase 7 accessibility,
SEO, privacy, disclaimer and visual requirements without changing the site.
The validation must distinguish:

1. authenticated preview evidence for the actual LegalKural pages and post;
2. anonymous evidence for the current Coming Soon surface; and
3. checks that cannot be completed anonymously until the separately controlled
   B11 launch checkpoint.

## Fixed target

- Site: `https://lkaidpl.wordpress.com`.
- Active theme: Assembler; inspection only.
- Certified article: WordPress post ID `10`.
- Certified slug: `end-use-over-label-hostels-are-homes`.
- Coming Soon: must remain active.
- Search indexing: must remain blocked.
- `tamil_rendered = false`.
- `thirukkural_algorithm_usage = TITLE_ONLY`.

## Permitted read-only inspection

### Authenticated preview

- Capture desktop and narrow/mobile screenshots of Home and post ID `10`.
- Inspect visible header, footer, navigation, headings, body copy, links and
  disclaimers without opening edit mode for any entity.
- Check visible heading hierarchy, readability, clipping, overflow, spacing and
  keyboard focus where inspection can be performed without saving state.
- Inspect the remaining structural pages already present in the approved
  information architecture, without editing them.

### Anonymous surface

- Open the site in a signed-out/private browser context.
- Confirm that the anonymous visitor sees Coming Soon rather than protected
  site content.
- Confirm no protected draft, private editor state or credential-bearing URL is
  exposed.
- Do not bypass, disable or temporarily remove Coming Soon.

### SEO, privacy and disclaimer evidence

- Inspect existing page titles, descriptions, canonical/robots signals and
  visible legal disclaimers where available without mutation.
- Compare observations with
  `PHASE_7_B5_ACCESSIBILITY_SEO_PRIVACY_AND_DISCLAIMER_SPECIFICATION.md` and
  `phase7-b7/SEO_METADATA_MATRIX.json`.
- Record absent, ambiguous, inaccessible or launch-deferred evidence as a
  finding; do not repair it in B9.
- Treat full anonymous content-level SEO and accessibility validation as
  deferred when Coming Soon prevents anonymous access.

## Evidence requirements

- Inspection timestamp and operator.
- Authenticated desktop and narrow/mobile screenshots.
- Anonymous Coming Soon screenshot.
- Per-route checklist with PASS, FAIL, BLOCKED or DEFERRED status.
- Explicit list of controls that could not be inspected anonymously.
- Confirmation that post ID `10` identity and publication state were not
  changed.
- Confirmation that Coming Soon and indexing were unchanged.
- Provider/WordPress mutation request count: `0`.
- Public launch actions: `0`.
- Credential, token and private-information redaction before repository use.

## Stop conditions

Stop immediately if:

- inspection requires saving, publishing or updating an entity;
- a control requests plan upgrade, custom CSS, theme replacement or media
  upload;
- Coming Soon or indexing would need to change;
- post ID `10`, its title, slug, status or certified identity differs;
- a credential, token, private URL or personal information would enter evidence;
- a CAPTCHA, security warning or account-recovery flow appears;
- the requested state cannot be distinguished from cached or authenticated
  state.

## Hard exclusions

- Site Editor or WordPress API mutation.
- Page, post, template, template-part, navigation, pattern or settings mutation.
- Theme or Global Styles mutation.
- SEO metadata, robots, canonical or structured-data mutation.
- Logo, favicon, site icon or media upload.
- Post ID `10` mutation.
- Tamil or literary Kural rendering.
- Coming Soon removal.
- Search-indexing activation.
- Public launch.

## Completion rule

B9 completes only when a separately approved repository-evidence boundary
records the observed results, deferred anonymous checks, protected-state
verification and zero-mutation evidence. B9 cannot approve B10 certification or
B11 launch.
