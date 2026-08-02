# WordPress End-to-End Publishing v1.0

## Flow

```text
LegalKural article
  -> category resolution
  -> tag resolution
  -> author resolution
  -> optional image upload
  -> optional source document + QR block
  -> metadata
  -> slug idempotency
  -> draft / publish / schedule
```

## Live command

```bash
export WORDPRESS_SITE_URL="https://example.com"
export WORDPRESS_USERNAME="admin"
export WORDPRESS_APPLICATION_PASSWORD="xxxx xxxx xxxx xxxx"

./bin/legalkural-wordpress-pipeline \
  article-package.json \
  --allow-live
```

## Sprint closure rule

Automated tests close the implementation package.
Sprint 50 is fully closed only after one live WordPress
draft or publication succeeds using founder-provided credentials.
