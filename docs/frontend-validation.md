# Frontend Validation

Use this guide when migrating frontend structure or reviewing frontend source
ownership changes.

## Targeted Phase Checks

Run structure and import-boundary tests after source movement:

```bash
cd frontend
npm test -- tests/component/frontend-structure.test.ts tests/component/frontend-import-boundaries.test.ts
```

Run source-boundary scans after import rewrites:

```bash
rg '@/components|@/lib|app/styles|features/i18n/messages' frontend/src frontend/tests frontend/components.json
```

The scan should return no matches.

Run focused component tests for migrated collaboration and locale areas:

```bash
cd frontend
npm test -- tests/component/collaboration-documents.test.tsx
npm test -- tests/component/collaboration-paper-library.test.tsx
npm test -- tests/component/research-assets-locale.test.tsx
```

Run focused Playwright workflows when route or feature imports change:

```bash
cd frontend
npm run test:e2e -- collaboration-documents.spec.ts
npm run test:e2e -- collaboration-paper-library.spec.ts
npm run test:e2e -- research-assets-locale.spec.ts
```

Run static checks after import, style, or config changes:

```bash
cd frontend
npm run lint
npm run build
```

## Final Frontend Gate

```bash
cd frontend
npm run lint
npm test
npm run test:e2e
npm run build
```

From the repository root:

```bash
sh scripts/check-generated-artifacts.sh --clean
sh scripts/check-generated-artifacts.sh
```

## Expected Source Boundaries

- `src/app` contains application bootstrap, providers, and shell code only.
- `src/routes` owns routing and protected route policy.
- `src/features` owns business workflow code.
- `src/shared` owns cross-feature UI, API, utility, and platform infrastructure.
- `src/data` owns static display and locale configuration.
- `src/styles` owns global CSS, theme variables, and Tailwind entry styles.
- `src/shared` must not import from `src/features`.
- `src/data` must not contain React components, hooks, API calls, or mutable
  workflow state.
- `src/styles` must not import feature code.
- Generated build, coverage, screenshot, temporary database, and test-result
  artifacts must not remain in source scope.
