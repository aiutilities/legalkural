# Legal Kural ThinkingOS Engine

## Version

0.1.0

## Current Capability

The engine accepts one judgment PDF and creates:

- a verified local copy of the source;
- a SHA-256 integrity record;
- a case manifest; and
- the 11 standard artifact paths.

AI generation is not yet enabled.

## Usage

```bash
./bin/legalkural \
  path/to/judgment.pdf \
  --case-id LK-REF-0002
```
