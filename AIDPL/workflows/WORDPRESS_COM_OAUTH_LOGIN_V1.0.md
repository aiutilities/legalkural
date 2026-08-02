# WordPress.com OAuth Login v1.0

## Commands

```bash
./bin/legalkural-wordpress-com login
./bin/legalkural-wordpress-com whoami
./bin/legalkural-wordpress-com logout
```

## Required environment

```bash
export WORDPRESS_COM_CLIENT_ID="..."
export WORDPRESS_COM_CLIENT_SECRET="..."
export WORDPRESS_COM_REDIRECT_URI="http://localhost:8080/callback"
export WORDPRESS_COM_SITE_IDENTIFIER="lkaidpl.wordpress.com"
```

## Token storage

Default:

```text
generated/wordpress/oauth.json
```

The token file is created with mode `0600`.

Do not commit the token file.
