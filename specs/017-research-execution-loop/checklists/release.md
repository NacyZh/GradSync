# Feature 017 Release Verification

- [x] Django system check passes.
- [x] `makemigrations --check --dry-run` reports no changes.
- [x] Ruff passes for backend applications and tests.
- [x] Backend full suite passes: 562 tests.
- [x] Strict OpenAPI drift check passes all 41 operations with zero schema errors.
- [x] Frontend ESLint and production build pass.
- [x] Frontend component suite passes: 195 tests across 35 files.
- [x] PWA offline shell validation passes with 18 versioned assets.
- [x] Full-stack Playwright release matrix passes: 45 tests, with 3 fixture-based
  scenarios skipped by their existing environment guards.
- [x] Generated-artifact guard passes and reports feature 017 as blocked rather
  than manufacturing acceptance.
- [ ] `migrate --plan` requires a running PostgreSQL service; the local attempt
  stopped at database connection before evaluating the plan.
- [ ] Production readiness, backup restore, rollback, and smoke require the production host.
- [x] Production acceptance enforcement passes for the explicitly accepted
  Product, Testing, and Development decisions on the current revision.
