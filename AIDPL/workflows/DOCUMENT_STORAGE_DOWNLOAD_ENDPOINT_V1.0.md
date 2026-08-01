# Document Storage + Download Endpoint v1.0

## Lifecycle

```text
Converted document package
        ↓
Register in document store
        ↓
Approve
        ↓
Publish
        ↓
Stable endpoint becomes available
        ↓
Withdraw when necessary
```

## Public URL Pattern

```text
/documents/<document-id>/<published-filename>.pdf
```

## Commands

```bash
./bin/legalkural-document-store \
  --store-root storage/documents \
  register generated-documents/DOC-...

./bin/legalkural-document-store \
  --store-root storage/documents \
  approve DOC-...

./bin/legalkural-document-store \
  --store-root storage/documents \
  publish DOC-...

./bin/legalkural-document-server \
  --store-root storage/documents \
  --host 127.0.0.1 \
  --port 8787
```

## Safety

- Draft and approved documents are not downloadable.
- Only published documents resolve.
- Withdrawn documents stop resolving.
- Duplicate IDs with different checksums are rejected.
- Filename must match the registered publication record.

## Production Note

This v1 endpoint uses local storage and Python's standard HTTP server.
Production deployment will later replace this transport with object storage,
CDN delivery and authenticated administration.
