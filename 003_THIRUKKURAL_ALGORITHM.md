# 003 — Thirukkural-Inspired Title Algorithm

## Status

`CANONICAL — NORMATIVE`

## Exact Scope

The LegalKural Thirukkural-inspired algorithm is a governed editorial naming
mechanism. Its only permitted output is one original English article title.

`thirukkural_algorithm_usage = TITLE_ONLY`

`tamil_rendered = false`

## Inputs

The algorithm may use only verified, finalized artifacts representing:

- the controlling issue;
- the Court's reasoning;
- the holding and operative decision;
- the practical legal principle; and
- the limits or conditions attached by the Court.

## Method

1. Extract the controlling contrast, duty, consequence or legal principle.
2. Reduce it to one faithful proposition without adding a new rule.
3. Express that proposition as a concise, memorable English title.
4. Check the title against the holding, reasoning and decision artifacts.
5. Reject ambiguity, sensationalism, unsupported causation and overstatement.
6. Submit the title for editorial and Founder approval.

## Output Rules

The title must:

- be English-only;
- be original LegalKural editorial writing;
- reflect the verified legal meaning;
- avoid party defamation and clickbait;
- avoid claiming to quote the Court unless it is an exact verified quotation;
- avoid presenting itself as an authentic Thirukkural verse or translation;
- avoid numbering itself as a Kural; and
- remain within the title field of the governed output.

## Prohibited Outputs

The algorithm must not produce or insert:

- Tamil text;
- a two-line couplet;
- transliteration;
- an alleged or simulated Thirukkural verse;
- an epigraph, subtitle, body paragraph or footer text;
- legal reasoning not present in verified artifacts; or
- personalised legal advice.

## Failure Rules

If the verified artifacts do not support a faithful title, the algorithm must
fail closed and request editorial intervention. It must not fall back to a
generic, invented or model-derived principle.

## Evidence

The output record must preserve the case ID, source artifact hashes, algorithm
usage value `TITLE_ONLY`, `tamil_rendered: false`, reviewer decision and final
approval lineage.

## Authoritative Sources

This contract consolidates `AIDPL/agents/LK-KURAL.md`, Kural worker and review
workflows, implemented schemas and the Founder correction that LegalKural does
not require Tamil rendering or Kural-style body text.
