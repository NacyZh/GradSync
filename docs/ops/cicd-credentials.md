# CI/CD Credentials And Deployment Gates

Production deployment is controlled by the protected `production` GitHub
environment.

## Required GitHub Secrets

| Name | Purpose | Scope |
|------|---------|-------|
| `GRADSYNC_REGISTRY_TOKEN` | Push backend and frontend images to the registry | Repository or production environment |
| `PRODUCTION_DEPLOY_SSH_KEY` | Connect to the production host as deploy user | Production environment only |
| `PRODUCTION_ENV_FILE` | Render `.env.production` on the host | Production environment only |

## Required GitHub Variables

| Name | Purpose |
|------|---------|
| `GRADSYNC_PRODUCTION_HOST` | Production host or ingress target |
| `GRADSYNC_PRODUCTION_USER` | SSH user, defaults operationally to `deploy` |

## Gate Rules

- Pull requests run tests, builds, audits, and image scans but do not push or
  deploy images.
- Pushes to `main` publish immutable SHA image tags.
- The `deploy-production` job requires GitHub environment approval before
  deployment credentials are usable.
- Registry and deploy credentials must be least privilege and rotated after
  staff changes or suspected exposure.
- Rollback requires credentials capable of pulling the previous approved image
  tags and reusing the last known-good `.env.production`.
