# CI/CD Credentials And Deployment Gates

Production deployment is controlled by the protected `production` GitHub
environment.

## Required GitHub Secrets

| Name | Purpose | Scope |
|------|---------|-------|
| `PRODUCTION_DEPLOY_SSH_KEY` | Connect to the production host as deploy user | Production environment only |
| `PRODUCTION_ENV_FILE` | Render `.env.production` on the host | Production environment only |

## Required GitHub Variables

| Name | Purpose |
|------|---------|
| `GRADSYNC_PRODUCTION_HOST` | Production host or ingress target |
| `GRADSYNC_PRODUCTION_USER` | SSH user, defaults operationally to `deploy` |
| `GRADSYNC_PRODUCTION_SSH_PORT` | SSH port, defaults to `22` |
| `GRADSYNC_DEPLOY_PATH` | Repository path on the production host |
| `GRADSYNC_PUBLIC_URL` | Public URL used by post-deploy smoke checks |
| `GRADSYNC_STRICT_UPLOAD_PROXY_CHECK` | Optional `true` to fail deployment when the public proxy rejects the 3 MiB upload probe |

## Gate Rules

- Pull requests run tests and builds but do not deploy.
- Pushes to `master` deploy by SSH after backend and frontend checks pass.
- The `deploy-production` job requires GitHub environment approval before
  deployment credentials are usable.
- Deploy credentials must be least privilege and rotated after staff changes or
  suspected exposure.
- Rollback requires server Git access and the last known-good `.env.production`.
