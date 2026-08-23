# Phase 7 B5 — Accessibility, SEO, Privacy and Disclaimer Specification

## Status

`APPROVED — FOUNDER APPROVED`

The Founder explicitly approved this specification on 2026-08-19.
Repository synchronization of this documentation is authorized. B6 live
read-only WordPress inspection still requires separate explicit approval, and
no site mutation, publication, Coming Soon removal or public launch is
authorized.

This is an offline implementation specification. It authorizes no WordPress
login, API call, browser action, provider request, content mutation,
publication, Coming Soon removal or public launch.

## Authority and Identity

This specification implements the Founder-approved Phase 7 brand and website
blueprint without changing its decisions:

- canonical brand: `LegalKural`;
- tagline: `The court records events. We reveal their meaning.`;
- direction: contemporary legal-tech;
- palette: navy, teal and white;
- product role: source-grounded legal knowledge and interpretation;
- LegalKural is not a law firm, court, government service or legal-advice
  provider.

The approved blueprint remains the visual and information-architecture source
of truth. This document supplies the acceptance rules needed for B6 inspection
and the later governed WordPress implementation blocks.

## B5 Deliverables

B5 defines:

1. accessibility and responsive acceptance criteria;
2. page-level SEO and sharing metadata;
3. indexation, canonical and structured-data rules;
4. Privacy page content requirements;
5. Disclaimer page content requirements;
6. footer and article-level legal notices;
7. validation evidence required before public launch.

B5 does not create pages, themes, logos, images or live metadata.

## Accessibility Target

The implementation target is WCAG 2.2 Level AA. Conformance must not be claimed
until the implemented public pages have been tested. Automated checks are
necessary but do not replace keyboard, screen-reader, zoom and visual review.

### Structure and navigation

- Every page has one descriptive `h1`.
- Heading levels follow a logical hierarchy without styling-only headings.
- A keyboard-visible “Skip to content” link is the first focusable control.
- Header, primary navigation, main content and footer use semantic landmarks.
- Navigation labels remain consistent across desktop and mobile layouts.
- The current page is identifiable without relying on colour alone.
- Breadcrumbs, when present, use an ordered list and identify the current page.
- Repeated cards expose unique, meaningful link names.

### Keyboard and focus

- All interactive controls operate with a keyboard.
- Focus order follows reading order and never enters hidden mobile navigation.
- Focus indicators are clearly visible against white, mist, navy and teal
  surfaces.
- No keyboard trap is permitted.
- Menus, search and disclosures expose state programmatically.
- Focus is not obscured by sticky headers, cookie notices or overlays.
- Target size is at least 24 by 24 CSS pixels, with 44 by 44 preferred for
  primary touch actions.

### Colour and typography

- Normal text meets a minimum 4.5:1 contrast ratio.
- Large text and essential graphical objects meet a minimum 3:1 ratio.
- Teal `#087E8B` is not assumed accessible for every size/background; use the
  approved darker teal `#066872` where testing requires it.
- Meaning, status and links never depend on colour alone.
- Body text remains readable at 200% zoom and with increased text spacing.
- Pages reflow without horizontal scrolling at a 320 CSS-pixel viewport,
  except for genuinely two-dimensional content.
- Article body measure should remain approximately 60–75 characters per line.

### Images, icons and media

- Informative images have concise, purpose-specific alternative text.
- Decorative images use empty alternative text.
- The LegalKural logo alternative text is `LegalKural` and must not repeat the
  adjacent visible wordmark.
- Linked images describe the link destination or action.
- Icons have accessible names when they function as controls.
- Court emblems, seals or imagery that could imply affiliation are prohibited.
- Video or audio introduced later requires captions/transcripts as applicable.

### Forms, search and feedback

- Every field has a persistent programmatic label.
- Required state and validation errors are conveyed in text and associated with
  the relevant field.
- Error summaries receive focus when submission fails.
- Search has an accessible name; result counts and empty states are announced
  meaningfully.
- Placeholder text is not used as the only label.
- Authentication, CAPTCHA or subscription controls are out of scope unless
  separately approved and accessibility-tested.

### Motion, timing and responsive behaviour

- Essential information is not presented only through animation.
- Respect `prefers-reduced-motion` for non-essential transitions.
- No auto-rotating carousel, autoplay media or time-limited interaction is
  permitted in the launch baseline.
- Mobile navigation must preserve every primary destination and legal link.
- Content order remains the same semantically across breakpoints.

## Information Architecture and Page Metadata Matrix

Every page requires a unique title, description, canonical URL and sharing
preview. Final URLs must be confirmed during B6 before implementation.

| Page | H1 intent | Recommended title pattern | Indexation | Structured data candidate |
| --- | --- | --- | --- | --- |
| Home | Brand promise | `LegalKural — Legal meaning beyond the record` | index, follow | `WebSite`, `Organization` |
| Judgments | Browse verified explanations | `Judgments explained — LegalKural` | index, follow | `CollectionPage` |
| Judgment/article | Exact editorial title | `{Article title} — LegalKural` | index only after certification | `Article` |
| Journal | Browse editions | `LegalKural Journal` | index, follow | `CollectionPage` |
| Journal edition | Edition identity | `{Edition title} — LegalKural Journal` | index after archive verification | `CreativeWork` or no markup |
| About | Product identity and method | `About LegalKural` | index, follow | `AboutPage`, `Organization` |
| Methodology | Source and QA method | `How LegalKural works` | index, follow | `WebPage` |
| Privacy | Data-handling notice | `Privacy — LegalKural` | index, follow | `WebPage` |
| Disclaimer | Legal limitations | `Disclaimer — LegalKural` | index, follow | `WebPage` |
| Search results | User query results | `Search results — LegalKural` | noindex, follow | none |
| Draft/preview/system page | Non-public state | Descriptive internal title | noindex, nofollow | none |

## SEO and Sharing Contract

### Titles and descriptions

- Each indexable page has a unique, human-readable title.
- Put the page subject before the brand except on the home page.
- Avoid keyword repetition and unsupported claims such as “official,” “court
  approved,” “legal advice” or guaranteed accuracy.
- Each page has a concise, page-specific meta description that accurately
  summarizes visible content; do not treat a fixed character count as a
  guarantee of how search engines display snippets.
- The visible `h1`, title and description must describe the same page intent.
- Meta keywords are not required.

### Canonical and indexation

- Every indexable page has one absolute HTTPS self-referencing canonical URL.
- Canonical URLs use the final preferred hostname, path and trailing-slash
  convention observed during B6.
- Drafts, previews, search results, duplicate archives and utility pages must
  not compete with canonical editorial pages.
- No public URL may canonicalize to a Coming Soon or authentication page.
- XML sitemap membership must match approved indexation.
- `robots.txt`, page-level robots directives and platform privacy settings must
  not conflict.
- Removing Coming Soon and enabling indexing are separate final-launch actions.

### Social sharing

- Provide Open Graph title, description, canonical URL, type and image where
  WordPress.com permits.
- Provide equivalent X/Twitter card metadata where the platform permits.
- Sharing text must not imply court, government or professional affiliation.
- The default sharing image follows the approved navy/teal/white design and
  remains subject to a separate asset approval.
- Article images must be relevant to the visible article and have accurate
  alternative text.

### Structured data

- Use JSON-LD only when WordPress.com permits safe insertion and validation.
- Markup must describe content visible on the same page.
- `Organization` must identify LegalKural as a legal-knowledge platform, not a
  law firm, court or government body.
- `Article` fields should include headline, date published, date modified,
  author/editor identity where approved, image where approved and canonical
  URL.
- Do not use `LegalService`, ratings, claims of official status or invented
  credentials.
- Structured data is an enhancement, not a B5 or launch blocker when the
  WordPress.com plan cannot support it safely.

### Editorial SEO integrity

- Publication requires the existing certified LegalKural workflow and Founder
  gate; SEO fields never bypass legal fidelity or QA.
- Titles, excerpts, slugs, categories and tags must remain consistent with the
  certified publication metadata.
- Source judgment identity, court, decision date and case reference remain
  visible and accurate.
- Updates that materially change an article must preserve revision governance
  and use an accurate modified date.
- No SEO copy may overstate holdings, remove qualifications or turn explanation
  into legal advice.

## Privacy Specification

The Privacy page must be written from the actual B6-observed data flows. It must
not claim that no data is collected if WordPress.com, embedded content, forms,
analytics, cookies or server logs collect data.

### Required Privacy page sections

1. identity and contact channel for the site operator;
2. scope and effective/last-updated date;
3. information submitted directly by visitors;
4. information collected automatically by WordPress.com and enabled services;
5. purposes for processing and operating the site;
6. cookies and similar technologies, including platform-controlled cookies;
7. embedded content and external links;
8. service providers and disclosures;
9. retention principles;
10. security limitations;
11. visitor choices and applicable rights;
12. children’s privacy position;
13. cross-border/platform processing where applicable;
14. changes to the notice;
15. contact and grievance route where legally required.

### Privacy implementation rules

- Inventory forms, comments, subscriptions, analytics, embeds, sharing widgets
  and cookies during B6 before drafting final factual wording.
- Disable unnecessary collection and integrations by default.
- Never publish credentials, access tokens, private evidence paths or personal
  data from source material.
- Do not expose WordPress usernames or operational email addresses unless they
  are deliberately selected public contacts.
- Cookie/consent behaviour must be tested in an anonymous browser and must not
  obscure content or keyboard focus.
- The footer links to Privacy from every public page.
- Material data-practice changes require a notice update and new effective date.

## Disclaimer Specification

### Required site-wide meaning

The Disclaimer page and article-level notice must communicate clearly that:

- LegalKural provides general, informational legal knowledge and interpretation;
- content is not legal advice and does not create a lawyer-client relationship;
- users should consult a qualified legal professional for advice on specific
  facts, rights, remedies, deadlines or proceedings;
- source judgments and official records govern if any difference exists;
- summaries may omit facts, arguments, procedural history or later legal
  developments;
- users must independently verify current law, citations and case status;
- LegalKural is not affiliated with or endorsed by any court, tribunal,
  government body or official reporter unless expressly stated and evidenced;
- the Thirukkural-inspired algorithm is restricted to the English article title; no literary body content is generated;
- external links are provided for convenience and are not endorsements;
- availability, completeness and error-free operation are not guaranteed.

### Approved short article notice

> This LegalKural explanation is for general information, not legal advice.
> The source judgment and official record govern. Verify current law and obtain
> professional advice for your circumstances. The Thirukkural-inspired algorithm is restricted to the English article title.

The final live wording may be expanded after legal review but must not weaken
these four points.

### Placement

- The complete Disclaimer is linked from the global footer.
- The short notice appears after every judgment explanation and before or near
  source references.
- About and Methodology pages repeat the independence/no-affiliation statement.
- Search cards need not repeat the full notice but must not use advice-like
  calls to action.

## Footer Contract

The global footer contains:

- LegalKural identity and one-sentence description;
- links to About, Methodology, Judgments and Journal;
- Privacy and Disclaimer links;
- an accessible contact route if approved;
- copyright notice using the actual operating entity/owner decision;
- no theme placeholder copy or misleading WordPress credit where the plan
  permits lawful removal;
- no claim of court, government, bar-council or law-firm status.

## Security and Credential Leakage Review

Before any mutation or launch:

- inspect page source, rendered content, media metadata and downloadable files;
- confirm no token, password, client secret, private email, local filesystem
  path, temporary evidence root or internal operator note is exposed;
- verify draft and preview URLs do not reveal unauthorized content;
- confirm external links use HTTPS where available;
- apply `rel` protections to untrusted new-window links where supported;
- preserve existing provider-request and Founder-approval boundaries.

## B6 Read-Only Inspection Evidence Required

B6 must record, without mutation:

1. active WordPress.com plan and theme;
2. current public/Coming Soon behaviour for anonymous visitors;
3. existing pages, menus, header, footer and homepage assignment;
4. actual canonical, title, description, robots and sharing metadata;
5. sitemap and platform visibility configuration;
6. theme typography, colours and responsive behaviour;
7. available Site Editor, CSS, logo, favicon and metadata controls;
8. current Privacy, cookie, analytics, form, comment and subscription behaviour;
9. backup/export and rollback options;
10. constraints that require plan, theme or provider decisions.

B6 evidence must not contain access tokens, cookies or credentials.

## Later Implementation Sequence

1. B6 — separately approved live read-only WordPress inspection.
2. B7 — offline asset/content preparation and rollback plan.
3. B8 — separately approved, reversible site implementation.
4. B9 — anonymous visual, accessibility, SEO and privacy validation.
5. B10 — certification and operator handover.
6. B11 — Founder approval for Coming Soon removal and public launch.

No earlier block implicitly authorizes a later block.

## Acceptance Checklist

### Accessibility

- [ ] WCAG 2.2 AA test matrix completed for representative pages.
- [ ] Keyboard-only navigation and visible focus pass.
- [ ] Screen-reader landmark, heading, link and form review pass.
- [ ] 200% zoom, text spacing and 320 CSS-pixel reflow pass.
- [ ] Contrast and non-colour communication pass.
- [ ] Images and controls have correct accessible names.

### SEO and sharing

- [ ] Unique titles, descriptions and `h1` values verified.
- [ ] Canonical URLs and preferred hostname verified.
- [ ] Robots directives, visibility and sitemap agree.
- [ ] Open Graph/sharing previews verified where supported.
- [ ] Structured data, if used, validates and matches visible content.
- [ ] Certified article metadata and source identity remain unchanged.

### Privacy and disclaimer

- [ ] Actual data/cookie/integration inventory completed.
- [ ] Privacy notice matches observed behaviour.
- [ ] Global footer links work on desktop and mobile.
- [ ] Full and short disclaimers are present in required locations.
- [ ] No affiliation or legal-advice implication remains.
- [ ] Credential and personal-data leakage review passes.

### Governance

- [ ] Rollback evidence exists before live mutation.
- [ ] WordPress/provider requests are separately authorized.
- [ ] Coming Soon remains active until B11 Founder approval.
- [ ] Full engine regression remains at or above `557 passed`.

## Reference Baseline

- W3C Web Content Accessibility Guidelines 2.2:
  `https://www.w3.org/TR/WCAG22/`
- W3C WCAG overview:
  `https://www.w3.org/WAI/standards-guidelines/wcag/`
- Google Search metadata guidance:
  `https://developers.google.com/search/docs/crawling-indexing/special-tags`
- Google structured-data guidance:
  `https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data`
- Google Article structured-data guidance:
  `https://developers.google.com/search/docs/appearance/structured-data/article`

These external references guide later validation but do not override observed
WordPress.com plan limitations or LegalKural governance.

## Approval Gate

Founder approval is required before this specification is committed. Approval
of B5 authorizes documentation synchronization only. B6 live read-only
inspection still requires a separate explicit approval. No WordPress mutation,
publication, Coming Soon removal or public launch is authorized by B5.
