# 008 — WordPress Pipeline Contract

## Status

`CANONICAL — NORMATIVE`

## Purpose

The WordPress pipeline transfers an approved LegalKural article to an approved
site while preserving editorial approval, taxonomy, identity, idempotency,
security and publication evidence.

## Provider Boundary

Supported providers must be selected explicitly. The current pilot uses
WordPress.com with an explicit site identifier. Provider configuration,
credentials and OAuth material must never be written into public content,
committed evidence or logs.

## Required Sequence

1. Verify the finalized article and upstream artifact hashes.
2. Resolve and verify the exact site and provider.
3. Resolve an existing approved WordPress author.
4. Resolve or create only explicitly approved categories and tags.
5. Build and validate the deterministic WordPress payload.
6. Present the exact payload for human review.
7. Require explicit authorization for draft creation.
8. Create or update the private draft idempotently.
9. Read back and verify title, slug, content, author, taxonomy and status.
10. Apply approved presentation cleanup without changing legal meaning.
11. Require a separate explicit authorization for public publication.
12. Publish idempotently and read back the public state.
13. Record immutable publication evidence and hashes.

## Approval Boundaries

Approval is action-specific. Site selection, author selection, taxonomy
creation, draft creation, draft cleanup, publication and public launch are
separate decisions. Silence or an earlier approval is not reusable authority.

## Content Contract

- Public editorial output is English-only.
- `tamil_rendered: false`.
- Thirukkural algorithm usage is `TITLE_ONLY` and affects the title only.
- The WordPress pipeline must not generate new legal analysis.
- Legal meaning, page references, decision limits and disclaimer must survive
  WordPress block serialization.

## Idempotency

Retries must not create duplicate posts, media, categories or tags. Operations
must resolve existing remote objects using stable identifiers and verify remote
state before mutation.

## Evidence

Publication evidence must include:

- case ID and provider/site identity;
- payload path and SHA-256;
- source article/content SHA-256;
- post ID, slug, status and public URL;
- author, categories and tags;
- draft/publication timestamps;
- relevant remote response identity; and
- evidence SHA-256.

Evidence must exclude access tokens, secrets and unnecessary personal data.

## Failure and Rollback

Unexpected site identity, permission, schema, taxonomy, author, content,
idempotency or read-back mismatch must fail closed. Live visual or structural
changes require a pre-change snapshot, exact mutation plan, explicit approval,
GET-only verification and a tested rollback route.

## Website Launch Boundary

Publishing content does not authorize public site launch. Removing Coming Soon,
enabling indexing, switching theme, changing global styles, altering certified
post content or otherwise exposing the final site requires its own approved
Phase 7 gate.

## Authoritative Sources

This contract consolidates the WordPress publishing foundation, REST/provider
adapters, metadata/idempotency/media workflows, end-to-end workflow, Phase 7
implementation-and-rollback plan and certified publication evidence contract.
