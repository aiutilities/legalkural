# 007 — Output Specification

## Status

`CANONICAL — NORMATIVE`

## Output Set

For each case, the governed pipeline produces versioned artifacts for:

1. metadata;
2. timeline;
3. facts;
4. issues;
5. evidence;
6. law;
7. reasoning;
8. decision;
9. title-generation evidence;
10. article;
11. review, learning and publication evidence as applicable.

Machine-readable artifacts must conform to their repository schemas. Markdown,
HTML, PDF and WordPress payloads must be reproducible from verified inputs.

## Universal Fields

Every finalized output must preserve, directly or through its manifest:

- schema or contract version;
- case ID and source-document hash;
- producing component/version;
- creation/finalization timestamp;
- upstream artifact paths and hashes;
- review and approval state; and
- its own deterministic hash where specified.

## Legal Content Requirements

- Facts, issues, law, reasoning and decision must remain distinct.
- Substantive claims require source-page lineage.
- Party positions and Court findings require correct attribution.
- Holding, relief and limits must match the judgment.
- Missing source support must fail closed.

## Title Requirements

- One original English editorial title.
- Thirukkural algorithm usage: `TITLE_ONLY`.
- `tamil_rendered: false`.
- No Tamil, couplet, transliteration, epigraph or generated Kural body text.
- Final title requires review and approval.

## Article Requirements

The article must be readable, source-grounded and contain meaningful sections
covering the case, dispute, legal issues, governing law, reasoning, outcome,
practical meaning and limits where supported. It must include the approved
general-information/not-legal-advice disclosure.

Internal QA status, provider prompts, hidden reasoning, secrets and operational
credentials must never appear in public content.

## WordPress Payload Requirements

The payload must preserve title, slug, content, excerpt, author, category/tag
identifiers, discussion state and status. Draft creation and public publication
are separate approved actions. Publication evidence must record the returned
post ID, URL, timestamps, payload hash and relevant metadata.

## Journal Requirements

The weekly journal is English-only and uses finalized, eligible published
articles. Its manifest must preserve article order, publication lineage,
covered date range and hashes for assembly, PDF, evidence and manifest.

## Quality Gates

An output cannot advance when schema validation, source fidelity, legal review,
editorial review, deterministic-hash verification or required human approval
fails.

## Authoritative Sources

This specification consolidates implemented schemas, the AIDPL pipeline,
editorial review contracts, journal contracts and publication payload/evidence
contracts. Implemented schemas remain binding and may be stricter.
