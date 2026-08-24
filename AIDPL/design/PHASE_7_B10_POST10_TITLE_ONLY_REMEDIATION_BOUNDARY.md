# Phase 7 B10 Post-10 TITLE_ONLY Remediation Boundary

## Authorization

Founder authorization: `APPROVED`

Approved against checkpoint
`8fec4e1a5eb62af6184b6e030ae4130f96662da9` after Phase 7 B9 closed as
`COMPLETED_WITH_BLOCKING_TITLE_ONLY_DEFECT`.

This boundary authorizes one tightly controlled remediation of the published
WordPress post with post ID `10`. It does not authorize public launch.

## Exact target

- Site: `https://lkaidpl.wordpress.com`
- Post ID: `10`
- Published slug: `end-use-over-label-hostels-are-homes`
- Published title: `End-Use Over Label: Hostels Are Homes`
- Case ID: `LK-OPENAI-PILOT-0001`

No other post, page, template, style, navigation item, site setting or account
resource is within scope.

## Required pre-mutation evidence

Before any write:

1. Fetch the current authoritative post representation.
2. Save the complete pre-mutation response as immutable evidence.
3. Record the post ID, URL, slug, status, title, author, categories, tags,
   publication timestamp and modification timestamp.
4. Calculate SHA-256 for the complete pre-mutation response and for the exact
   current content field.
5. Confirm that the target still contains the B9-observed prohibited material.
6. Abort on target drift, authentication ambiguity, unexpected post status or
   mismatch of immutable metadata.

## Permitted mutation

Exactly one content update to post ID `10` is permitted. The update may remove
only the opening literary block comprising:

- the English editorial couplet or epigraph;
- the Tamil couplet;
- the statement describing English and Tamil editorial writing;
- the statement that the writing is inspired by the Thirukkural; and
- associated empty wrappers or whitespace created solely by those removals.

The resulting article must begin directly with its source-grounded legal
content. No replacement subtitle, epigraph, verse, couplet or literary text may
be inserted.

## Immutable content and metadata

The mutation must preserve, byte-for-byte where the WordPress representation
permits:

- published title, slug, URL, status and publication timestamp;
- author, categories and tags;
- Case Snapshot;
- legal questions and issues;
- judicial reasoning and governing tests;
- decision, relief and factual limits;
- all page references and source qualifications;
- Editorial Disclaimer and review provenance; and
- all remaining source-grounded article content and ordering.

No SEO, excerpt, featured-media, comment, sharing or discussion setting may be
changed.

## TITLE_ONLY postcondition

The remediated post must satisfy:

- `tamil_rendered = false`
- `thirukkural_algorithm_usage = TITLE_ONLY`
- no Tamil rendering;
- no couplet, verse, translation or transliteration;
- no epigraph, subtitle, footer or body literary rendering; and
- no claim that displayed prose is inspired by, adapted from or translated
  from the Thirukkural.

The Thirukkural algorithm may affect the title-selection process only. It must
not render literary content in the published article.

## Forbidden mutations

This boundary does not authorize:

- homepage or other page edits;
- theme, typography, color, layout or Site Editor changes;
- navigation or footer changes;
- category, tag, author, slug, date or status changes;
- search-indexing changes;
- Coming Soon removal;
- public launch;
- provider inference or content regeneration; or
- changes to any repository file during the live remediation operation.

## Post-mutation verification

After the single update:

1. Fetch the authoritative post representation again.
2. Save the complete post-mutation response and compute response/content
   SHA-256 values.
3. Prove that only the permitted literary block was removed.
4. Confirm all immutable metadata and preserved legal content.
5. Confirm the forbidden TITLE_ONLY markers are absent.
6. Perform authenticated desktop visual inspection of the article opening and
   its full structure.
7. Confirm anonymous desktop and mobile visitors still receive Coming Soon.
8. Confirm search indexing remains discouraged.
9. Record mutation count, WordPress request count and all evidence hashes.

## Failure and rollback

If any immutable content or metadata changes unexpectedly, immediately stop.
Rollback may restore only the complete captured pre-mutation post content and
must itself be separately evidenced. No compensating edits beyond restoring
the captured state are allowed.

## Completion gate

B10 may close only when:

- the authorized single-post mutation succeeds;
- post ID `10` passes the TITLE_ONLY postcondition;
- all preserved legal content and metadata verify unchanged;
- Coming Soon and indexing protections remain active;
- the evidence package verifies; and
- public launch remains unauthorized.

Expected live-operation safety values:

- targeted posts: `1`
- permitted post updates: `1`
- provider requests: `0`
- Site Editor mutations: `0`
- public-launch requests: `0`
- public launch authorized: `NO`
