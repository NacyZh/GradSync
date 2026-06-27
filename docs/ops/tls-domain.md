# TLS And Domain Readiness

Production traffic must be served from `https://gradsync.example.edu` or the
approved replacement domain.

## Required DNS

| Record | Value | Purpose |
|--------|-------|---------|
| `A` or `AAAA` for app domain | Production ingress address | Browser and API traffic |
| `CAA` | Approved certificate authority | Limit certificate issuance |
| Provider-specific mail DNS | SPF, DKIM, DMARC records | Email provider verification |

## TLS Termination

- Terminate HTTPS at the production ingress or reverse proxy in front of
  `frontend:8080`.
- Forward `X-Forwarded-Proto: https` and `X-Request-ID` to nginx and Django.
- Redirect HTTP to HTTPS before traffic reaches Django.
- Use a certificate with automatic renewal and alert on renewal failure.
- Keep `SECURE_HSTS_SECONDS` positive and include the production domain in
  `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `FRONTEND_ORIGIN`, and
  `PUBLIC_API_BASE_URL`.

## Validation

Run these checks before release approval:

```bash
curl -I http://gradsync.example.edu
curl -I https://gradsync.example.edu/healthz
curl -I https://gradsync.example.edu/api/readyz/
```

Expected results:

- HTTP returns a redirect to HTTPS.
- HTTPS presents a valid, unexpired certificate for the production domain.
- HSTS is present on HTTPS responses.
- `/healthz` returns 200 and `/api/readyz/` returns 200 only when database and
  Redis are reachable.
