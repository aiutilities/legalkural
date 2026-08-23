# Title Reasoning Worker v0.1

## Agent

`LK-KURAL`

## Inputs

Structured facts, issues, reasoning and decision artifacts.

## Outputs

The compatibility paths under `output/09-kural/` contain a source-grounded
editorial brief and exactly one algorithmic output: the English article title.

## Mandatory Boundary

- `thirukkural_algorithm_usage`: `TITLE_ONLY`
- `tamil_rendered`: `false`
- no couplet, verse, translation, transliteration, epigraph, subtitle, body
  paragraph or footer text
- human legal-fidelity and editorial review remain mandatory
