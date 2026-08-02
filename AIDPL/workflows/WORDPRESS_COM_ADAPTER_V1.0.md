# WordPress.com Adapter v1.0

## Purpose

Support public WordPress.com sites with custom domains through
the WordPress.com public API proxy without changing the existing
self-hosted WordPress client.

## Provider Modes

- `wordpress_org`
- `wordpress_com`

## WordPress.com API

Preferred site identifier:

- numeric WordPress.com site ID

Supported fallback:

- custom domain

Base URL:

```text
https://public-api.wordpress.com/wp/v2/sites/{site_identifier}
```

## Authentication

Use an OAuth2 Bearer access token.

Environment:

```bash
export WORDPRESS_PROVIDER="wordpress_com"
export WORDPRESS_COM_SITE_IDENTIFIER="56733028"
export WORDPRESS_COM_ACCESS_TOKEN="..."
```

Do not commit access tokens.

## Commands

```bash
./bin/legalkural-wordpress-com site
./bin/legalkural-wordpress-com posts --per-page 5
```

Draft creation and updates use JSON payload files.

## Production rule

The development password grant may be used only for a private
pilot. Production must use the OAuth2 Authorization Code flow.
