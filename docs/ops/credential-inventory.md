# Production Credential Inventory

This inventory defines where production secrets are landed outside the
repository before a release can be approved. Do not store secret values in this
file.

| Credential | Required Variable Or Secret | Owner | Storage Location | Rotation Trigger | Validation |
|------------|-----------------------------|-------|------------------|------------------|------------|
| Django signing key | `DJANGO_SECRET_KEY` | Application owner | Production secret manager path `gradsync/prod/django` | Planned application key rotation or suspected exposure | `python manage.py check_production_readiness` fails on defaults |
| PostgreSQL password | `POSTGRES_PASSWORD` | Database owner | Production secret manager path `gradsync/prod/postgres` | Staff change, suspected exposure, or scheduled database rotation | Database readiness check and migration command |
| Redis broker URL | `REDIS_URL` | Platform owner | Production secret manager path `gradsync/prod/redis` | Host move or suspected exposure | Celery worker and scheduler healthchecks |
| Email provider credential | `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Operations owner | Production secret manager path `gradsync/prod/email` | Provider key rotation or delivery incident | SMTP/provider probe to `PRODUCTION_SMTP_PROBE_TO` |
| Bounce webhook secret | `EMAIL_BOUNCE_WEBHOOK_SECRET` | Operations owner | Production secret manager path `gradsync/prod/email` | Provider webhook rotation | Provider webhook signature test |
| Error reporting DSN | `SENTRY_DSN` | Application owner | Production secret manager path `gradsync/prod/observability` | Sentry project rotation | Readiness check confirms error reporting initialization |
| Alert route | `ALERT_WEBHOOK_URL`, `ALERT_ONCALL_TARGET` | Operations owner | Production secret manager path `gradsync/prod/observability` | On-call vendor or roster change | Alert dry run reaches on-call target |
| Registry token | `GRADSYNC_REGISTRY_TOKEN` | Release owner | GitHub Actions production environment secret | Registry policy rotation | Release workflow login and image push |
| Deploy SSH key | `PRODUCTION_DEPLOY_SSH_KEY` | Platform owner | GitHub Actions production environment secret | Host rotation or staff change | Protected deployment job validates presence |
| Production env file | `PRODUCTION_ENV_FILE` | Release owner | GitHub Actions production environment secret | Any production config change | Deployment job writes env file on host |
| Backup storage credential | Provider-specific backup secret | Database owner | Production secret manager path `gradsync/prod/backup` | Storage policy rotation | Restore drill reads off-host encrypted backup |

## Release Rules

- Production releases must use the protected `production` GitHub environment.
- A named owner must verify every credential row before the first production
  deployment and after any rotation.
- `.env.production` is generated on the host from the secret manager or the
  protected deployment secret. It must never be committed.
- Rotation must be followed by `check_production_readiness`, a sign-in smoke
  test, and one notification delivery probe.
