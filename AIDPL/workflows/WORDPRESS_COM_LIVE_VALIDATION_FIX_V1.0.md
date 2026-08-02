# WordPress.com Live Validation Fix v1.0

## Finding

OAuth and post retrieval were successful.

The `site` command appeared incorrect because the WordPress.com
site root returns the complete REST route index. The subsequent
`posts` command also completed and returned a JSON array, so there
was no posts-routing failure.

## Fix

- `site` now returns a concise connectivity summary.
- `whoami` returns the same authenticated site summary.
- `site-raw` preserves access to the complete route index.
- `posts` remains unchanged.
