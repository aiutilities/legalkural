# WordPress REST Client v1.0

## Capabilities

- Application Password authentication
- Root health check
- Authenticated current-user check
- Create post
- Update post
- Draft, immediate publication and scheduled publication
- Bounded retry and timeout handling
- LegalKural content types:
  - Judgment
  - News
  - Column
  - Interview

## Environment

```bash
export WORDPRESS_SITE_URL="https://example.com"
export WORDPRESS_USERNAME="admin"
export WORDPRESS_APPLICATION_PASSWORD="xxxx xxxx xxxx xxxx"
export WORDPRESS_VERIFY_SSL="true"
export WORDPRESS_TIMEOUT_SECONDS="30"
export WORDPRESS_MAX_ATTEMPTS="3"
```

## Connectivity

```bash
./bin/legalkural-wordpress doctor
./bin/legalkural-wordpress me
```
