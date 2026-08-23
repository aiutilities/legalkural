# 005 — Legal Knowledge Graph Contract

## Status

`CANONICAL — NORMATIVE`

## Purpose

The LegalKural knowledge graph is the provenance-preserving relationship layer
connecting a source judgment to structured legal meaning, editorial outputs,
publication evidence and journal/archive records.

It is not permission to infer missing legal facts.

## Required Node Classes

- source document and source hash;
- case, court, bench, judge and party;
- procedural event and material fact;
- allegation, submission, evidence and document;
- issue, statutory provision, rule, precedent and legal test;
- observation, finding, reasoning step, holding and operative order;
- article, title, category, tag and author;
- WordPress draft/publication evidence;
- journal edition, manifest, PDF and archive entry; and
- reviewer, approval and correction event.

## Required Edge Semantics

Edges must use explicit meanings such as:

- `DERIVED_FROM`
- `SUPPORTED_BY_PAGE`
- `INVOLVES_PARTY`
- `RAISES_ISSUE`
- `GOVERNED_BY`
- `CITES`
- `ARGUES`
- `FINDS`
- `REASONS_TO`
- `HOLDS`
- `ORDERS`
- `LIMITED_BY`
- `EXPLAINED_IN`
- `PUBLISHED_AS`
- `INCLUDED_IN_EDITION`
- `REVIEWED_BY`
- `APPROVED_BY`
- `SUPERSEDES`

An edge name must not silently change an allegation into a finding or a cited
authority into an adopted rule.

## Provenance

Each legally substantive node or edge must preserve:

- case ID;
- originating artifact and immutable hash;
- source page reference where available;
- assertion type and attributed speaker;
- extraction or review timestamp;
- producing component/version; and
- human review state.

## Identity and Immutability

Identifiers must be stable within the case and deterministic where the
implemented schema requires it. Finalized artifacts, publication evidence and
archive entries are immutable. Corrections create a linked successor rather
than silently replacing certified history.

## Inference Boundary

Only explicitly implemented and reviewable relationships may be derived.
Unsupported predictive, causal or similarity edges are prohibited. Model
confidence is not source evidence.

## Query Boundary

Queries may summarize verified relationships, compare holdings or trace
lineage. They must preserve jurisdiction, procedural posture, date and
case-specific limits and must not produce personalised legal advice.

## Publication Relationship

WordPress IDs, URL, author, categories, tags, publication timestamp, source
payload hash and publication-evidence hash must remain linked to the certified
article and case.

## Authoritative Sources

This contract consolidates the structured LegalKural artifact pipeline,
schemas, publication metadata lineage, journal manifest lineage and archive
contracts. Where a schema is more restrictive, the schema prevails.
