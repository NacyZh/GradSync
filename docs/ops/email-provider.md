# Production Email Provider

Email is the required notification channel for GradSync. Production launch must
use a verified provider account rather than the local email sink.

## Provider Setup

| Requirement | Acceptance |
|-------------|------------|
| Sender domain verified | Provider shows `EMAIL_PROVIDER_DOMAIN` as verified |
| DKIM enabled | `EMAIL_DKIM_SELECTOR` DNS record validates |
| SPF aligned | SPF includes the provider send host |
| DMARC present | Domain has a DMARC record with an explicit policy |
| Sender address verified | `DEFAULT_FROM_EMAIL` can send without sandbox restrictions |
| Bounce handling configured | Provider webhook secret is stored as `EMAIL_BOUNCE_WEBHOOK_SECRET` |
| Rate limits documented | Expected reminder volume fits provider limits |

## Release Validation

1. Load provider credentials into production secrets.
2. Set `EMAIL_PROVIDER`, `EMAIL_PROVIDER_DOMAIN`, `EMAIL_DKIM_SELECTOR`,
   `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and
   `PRODUCTION_SMTP_PROBE_TO`.
3. Run:

   ```bash
   docker compose -f docker-compose.prod.yml run --rm backend python manage.py check_production_readiness --smtp-probe-to "$PRODUCTION_SMTP_PROBE_TO"
   ```

4. Confirm the probe message is delivered and visible in provider logs.
5. Submit one draft and confirm the advisor notification delivery record reaches
   `sent`.
