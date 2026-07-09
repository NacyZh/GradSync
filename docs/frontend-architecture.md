# Frontend Architecture

GradSync frontend code follows a Vite-oriented, feature-first structure. Vite
tooling stays at `frontend/`; runtime code stays under `frontend/src/`.

## Canonical Source Areas

| Path | Responsibility | Examples |
|------|----------------|----------|
| `frontend/src/app/` | Application bootstrap, providers, and top-level shell only | `main.tsx`, `App.tsx`, `Layout.tsx`, `queryClient.tsx` |
| `frontend/src/routes/` | Route registry, route guards, and access policy wiring | `index.tsx`, `ProtectedRoute.tsx` |
| `frontend/src/features/` | Business feature modules and feature-owned workflow code | `library/`, `projects/`, `resources/` |
| `frontend/src/shared/api/` | Cross-feature API client infrastructure | request client, download helpers, API errors |
| `frontend/src/shared/ui/` | Reusable product UI and shared UI primitives | app feedback, data states, form status, primitives |
| `frontend/src/shared/lib/` | Cross-feature utility functions | class name helpers |
| `frontend/src/shared/platform/` | Browser/platform infrastructure reused by features | storage, environment, telemetry hooks when present |
| `frontend/src/data/` | Static display data and multilingual configuration | locale messages, display option maps |
| `frontend/src/styles/` | Global CSS, theme variables, Tailwind entry styles | `globals.css`, `theme.css` |
| `frontend/src/assets/` | Source-controlled frontend assets | SVGs, images, static media |
| `frontend/src/test/` | Shared frontend test setup and fixtures | Vitest setup, collaboration fixtures |
| `frontend/tests/component/` | Broad component and integration tests | React Testing Library suites |
| `frontend/tests/e2e/` | Browser workflow tests | Playwright specs |

## Import Rules

- `src/app` may import from `src/routes`, `src/shared`, `src/data`, and
  `src/styles`.
- `src/routes` may import page targets from `src/features` and guards or helpers
  from `src/shared`.
- `src/features/<feature>` may import from `src/shared`, `src/data`, and its own
  feature-local files.
- Features must not import another feature's private internals. Move
  cross-feature reuse through `src/shared`.
- `src/shared` must not depend on feature-specific internals.
- `src/data` must not contain React components, hooks, API calls, or mutable
  workflow state.
- `src/styles` must not import feature code.

## Placement Self-Check

- Application entry point: `frontend/src/app/main.tsx`.
- Page routing: `frontend/src/routes/index.tsx`.
- Protected routes: `frontend/src/routes/ProtectedRoute.tsx`.
- Project workspace pages: `frontend/src/features/projects/`.
- Shared UI primitive: `frontend/src/shared/ui/primitives/button.tsx`.
- Shared product UI: `frontend/src/shared/ui/DataState.tsx`.
- Shared utility: `frontend/src/shared/lib/utils.ts`.
- Locale display config: `frontend/src/data/locale/messages.en.ts`.
- Global style token: `frontend/src/styles/theme.css`.
- Static asset: `frontend/src/assets/`.
- Shared test setup: `frontend/src/test/setup.ts`.
- Component test: `frontend/tests/component/`.
- End-to-end test: `frontend/tests/e2e/`.

## Placement Examples

| Change | Canonical location | Notes |
|--------|--------------------|-------|
| Add a project route | `frontend/src/routes/index.tsx` plus the owning feature page | Route registration stays centralized; page behavior stays feature-owned. |
| Add a feature component used only by library screens | `frontend/src/features/library/` | Keep local UI near the workflow it serves. |
| Add a reusable primitive button/dialog/input | `frontend/src/shared/ui/primitives/` | Use only when it is reusable across features. |
| Add reusable product UI such as empty/error state | `frontend/src/shared/ui/` | Shared product UI must not import feature internals. |
| Add a formatting or class-name helper | `frontend/src/shared/lib/` | Utilities here must have cross-feature value. |
| Add a locale label or static option map | `frontend/src/data/` | No React components, hooks, API calls, or mutable workflow state. |
| Add global theme variables | `frontend/src/styles/theme.css` | Global CSS must not import feature code. |
| Add an image or SVG asset | `frontend/src/assets/` | Keep source assets separate from generated build output. |
| Add shared Vitest setup or fixtures | `frontend/src/test/` | Runtime code must not import from this area. |
| Add a broad component workflow test | `frontend/tests/component/` | Use this for cross-module UI behavior. |
| Add a browser workflow test | `frontend/tests/e2e/` | Use this for route, auth, upload/download, and role workflows. |

## Review Expectations

Movement-only refactors must preserve route paths, visible labels,
authorization, form behavior, upload/download behavior, search behavior,
accessibility names, and persisted data semantics. Every moved area should have
an entry in `specs/009-frontend-structure-refactor/migration-map.md`.
