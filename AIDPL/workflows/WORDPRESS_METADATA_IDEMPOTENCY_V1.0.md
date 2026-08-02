# WordPress Metadata Resolution + Idempotency v1.0

## Scope

- Frozen category name to WordPress ID resolution
- Five-to-nine single-word tag resolution
- Optional creation of missing WordPress tags
- Admin and volunteer-editor author resolution
- LegalKural publication metadata
- Slug-based create-or-update behavior
- Local publication registry and fingerprint

## Idempotency Rule

```text
Existing slug
    -> update existing WordPress post

Missing slug
    -> create new WordPress post
```

Retries must not produce duplicate posts.
