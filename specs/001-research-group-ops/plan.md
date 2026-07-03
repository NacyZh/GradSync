# Implementation Plan: Research Group Operations

**Branch**: `001-research-group-ops` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-research-group-ops/spec.md`

## Summary

Build GradSync as a web application for graduate research group operations.
Advisors manage project membership and hierarchical task plans, students submit
versioned drafts and weekly progress reports, advisors review submissions with
inline comments, project records remain strictly isolated by project membership,
custom discipline-specific resources are booked without conflicts, paper and
code assets are imported from local folders into project-scoped team public
libraries, the interface can switch between Chinese and English immediately,
the login screen is production-ready with a full-viewport appropriate visual,
aligned controls, and password visibility support, Docker e2e seeding is
reliable, and email reminders cover pending reviews, approaching deadlines,
booking changes, and new submissions.

The implementation uses Django for backend domain logic and project-scoped
authorization, React with TypeScript and Vite for the web application,
PostgreSQL for durable relational records, Redis for background job coordination
and transient state, and Docker Compose for local and deployment orchestration.

## Technical Context

**Language/Version**: Python 3.12 for Django backend; TypeScript 5.x for React
web frontend

**Primary Dependencies**: Django 5.x, Django REST Framework, Celery, django-celery-beat,
django-celery-results, Redis client, PostgreSQL driver, React 18, Vite 5,
React Router, TanStack Query, React Hook Form, Zod, Tailwind CSS,
shadcn/ui, Radix UI primitives, class-variance-authority, lucide-react,
Vitest, Playwright, pytest, pytest-django; Django file storage abstraction for
paper/code attachments; local browser file/folder import handling in the
frontend backed by server-side import staging and checksum validation;
lightweight BibTeX/text metadata parsing implemented in the backend service
layer unless a later task selects a vetted parser; React i18n message catalog
support implemented with local typed dictionaries before adding a larger
translation framework; configurable SMTP or development email-capture backend
for notification delivery; repository-owned responsive login background asset
or equivalent generated bitmap visual with CSS fallback for authentication
screens.

**Frontend Architecture Decision**: This feature must deliver a production-grade
React/Vite architecture. Tailwind CSS and shadcn/ui provide the design-system
foundation, Radix UI primitives provide accessible component behavior,
lucide-react provides iconography, TanStack Query remains the server-state layer
for Django REST contracts, and React Hook Form/Zod remain the form validation
layer. The unauthenticated login route uses a centered form over a real
background visual that fills the viewport without remote hotlinking, uses
aligned input controls, exposes an accessible password show/hide action, and
supports production error/loading states. Redux Toolkit and RTK Query are not
introduced unless a later feature proves complex client-only state that cannot
be handled by route state, local component state, and TanStack Query.

**Storage**: PostgreSQL for users, projects, memberships, tasks, draft versions,
reports, inline comments, configurable resource types/items, bookings, paper
metadata, code artifact metadata, local import batch records, locale
preferences, email notifications, and audit records; managed Django file storage
or object-storage-compatible references for locally imported paper/code files;
Redis for Celery broker, reminder scheduling coordination, cache, retry
coordination, and short-lived locks

**Testing**: pytest and pytest-django for backend unit, contract, and integration
tests; Vitest and React Testing Library for frontend unit/component tests;
Playwright for end-to-end project isolation, submission review, booking, paper
library local-folder import, code library local-folder import with descriptions,
download authorization, real-time language-switching flows, centered login
layout with password visibility, responsive layout reasonableness checks,
Docker `seed_e2e_research_ops` smoke validation, and email delivery/status
flows; contract tests against `contracts/openapi.yaml`

**Target Platform**: Docker Compose-managed web deployment with backend API,
frontend web app, PostgreSQL, Redis, and worker services

**Project Type**: Web application with Django backend and React/Vite frontend

**Performance Goals**: Project dashboard opens within 3 seconds for projects
with up to 500 active records; project-scoped search/filter completes within 2
seconds; paper/code library search completes within 2 seconds for up to 1,000
paper records and 250 code artifacts per project; duplicate detection for up to
100 locally imported paper metadata records completes within 10 seconds before
commit;
visible confirmation for common record updates appears within 2 seconds;
eligible reminder emails are queued or recorded within 5 minutes; the production
frontend shell must avoid avoidable layout shift, keep route-level code split
points explicit for large workspaces, and keep generated CSS limited to Tailwind
content scanning plus shadcn/ui components actually used by the app.

**Constraints**: Strict project isolation for all tasks, drafts, reports,
comments, bookings, papers, code artifacts, downloads, notifications, and
activity; no cross-project record linking except through explicit membership in
each project; overlapping custom resource bookings must be prevented; resource
types and fields must be configurable per professional context; paper/code
imports must come from explicit local file/folder selection and must not run
default automatic external search; paper import must reject duplicates with an
explainable match; downloads must re-check authorization and write audit events;
archived projects are read-only unless reopened; user locale changes must update
visible UI immediately without altering authorization or stored research
content; production login assets must be owned by the repository or build
pipeline and must fill the viewport without distorting form layout; Docker e2e
seed data must stay aligned with current migrations and model fields;
production flows must not include prototype-only copy or behavior; all
behavioral changes require automated tests

**Scale/Scope**: At least 50 active projects, 500 total project members, and
500 active operational records per project for the specified user journeys, plus
1,000 paper records and 250 code artifacts per project for library workflows.
Frontend workflows must support dense project operations on desktop and tablet
viewports, with responsive mobile access for review, notification, booking,
library lookup, downloads, and language switching.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code Quality**: PASS. Backend modules will be separated by domain
  responsibility (`projects`, `tasks`, `submissions`, `resources`, `library`,
  `repositories`, `notifications`, `audit`) with shared project-scope
  permission helpers, configurable resource schema services, local import
  staging services, file attachment services, checksum utilities, email
  delivery services, and download audit helpers.
  Frontend modules will mirror user workflows (`project dashboard`, `task tree`,
  `draft review`, `weekly reports`, `resource booking`, `paper library`, `code
  library`, `notifications`, `locale preferences`) and use typed contracts
  generated or checked from the OpenAPI document. Shared frontend primitives
  must live in `shared/ui`, be generated or adapted from shadcn/ui, and expose
  stable variants instead of one-off CSS. Non-obvious isolation, duplicate
  detection, local folder import, download authorization, immediate locale
  switching, production login composition, Docker e2e seed reliability, email
  delivery fallback, configurable resource validation, and booking conflict
  rules will be documented in domain services.
- **Testing**: PASS. Required coverage includes backend unit tests for hierarchy
  and state rules, contract tests for every public API operation, integration
  tests for project isolation, library duplicate detection, download
  authorization, immediate language switching, email delivery status, custom
  resource configuration, local folder import, Docker e2e seed command
  execution, and booking conflicts, frontend component tests for critical forms
  and states, and Playwright flows for advisor/student end-to-end journeys,
  login layout, and responsive workspace layout checks. No test gaps are
  approved.
- **User Experience**: PASS. Project context must remain visible on every
  project-scoped route. The web app will include advisor project management,
  student assigned work, review queues, and booking views with consistent
  navigation, keyboard support, labels, and loading/empty/error states. Paper
  and code library screens must support dense scanning, local folder/file import
  progress, duplicate explanations, metadata detail panels, download actions,
  and filtered empty states. Resource management screens must support custom
  type and field configuration. The authenticated shell must expose a
  keyboard-accessible Chinese/English language switcher that updates visible UI
  text immediately. The login screen must be centered over a full-viewport,
  production-appropriate background visual, align authentication controls, offer
  password visibility, and expose production authentication feedback.
  Tailwind CSS tokens and shadcn/ui components must provide a coherent,
  production-ready operations interface rather than prototype cards or placeholder
  layouts. Core routes must be checked for overlap, clipped controls, unstable
  action placement, and poor responsive density.
- **Performance**: PASS. Performance requirements from the spec are carried into
  backend query design, frontend data loading, file metadata indexing, duplicate
  detection, and quickstart validation. Search, dashboard, library, and locale
  views will be measured with seeded projects at target scale.
- **Architecture**: PASS. Django, React/Vite, PostgreSQL, Redis, and Docker
  Compose are user-selected stack choices and fit the web app scope. Celery is
  justified for reliable email and reminder processing outside request flows.

**Post-Design Re-check**: PASS. `research.md`, `data-model.md`,
`contracts/openapi.yaml`, `contracts/frontend-ui.md`, and `quickstart.md`
preserve the same gates. Project isolation is modeled as explicit membership
plus project foreign keys on every research record. Booking conflict prevention,
custom resource schemas, paper duplicate detection, code artifact versioning,
local folder import, download authorization, immediate locale preference
behavior, email notification delivery, production login/workspace shell
behavior, Docker e2e seed reliability, design-system composition, responsive UI
layout checks, and accessibility expectations are captured as contracts and
validation scenarios.

## Stakeholder Review and Release Risk

Project owner review is confirmed as of 2026-07-02. Formal testing stakeholder
review and formal development stakeholder review are still pending. This is a
tracked Constitution II release risk: implementation work may continue only with
the risk visible in this plan, and release remains blocked until testing and
development review are completed or an approved, time-bounded exception is
recorded.

## Project Structure

### Documentation (this feature)

```text
specs/001-research-group-ops/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml
│   └── frontend-ui.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
backend/
├── manage.py
├── pyproject.toml
├── gradsync/
│   ├── settings/
│   ├── urls.py
│   ├── celery.py
│   └── asgi.py
├── apps/
│   ├── accounts/
│   ├── projects/
│   ├── tasks/
│   ├── submissions/
│   ├── resources/
│   ├── library/
│   ├── repositories/
│   ├── notifications/
│   └── audit/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

frontend/
├── package.json
├── components.json
├── tailwind.config.ts
├── postcss.config.js
├── vite.config.ts
├── src/
│   ├── app/
│   ├── routes/
│   ├── features/
│   │   ├── projects/
│   │   ├── tasks/
│   │   ├── submissions/
│   │   ├── resources/
│   │   ├── library/
│   │   ├── repositories/
│   │   ├── i18n/
│   │   └── notifications/
│   ├── components/
│   │   └── ui/
│   ├── shared/
│   └── test/
└── tests/
    ├── e2e/
    └── component/

docker/
├── backend.Dockerfile
└── frontend.Dockerfile

docker-compose.yml
```

**Structure Decision**: Use a two-application web structure with a Django
backend and React/Vite frontend. Keep domain rules that protect project
isolation, version history, configurable resource schemas, booking conflicts,
paper duplicate detection, code artifact versioning, local import staging,
download authorization, locale preference persistence, and email notification
scheduling in backend domain services, while the frontend owns workflow
presentation, local file/folder selection, client-side validation, immediate
language message selection, production-grade login/workspace composition,
responsive layout behavior, and password visibility interaction.
The frontend uses Tailwind CSS for tokens/layout utilities, shadcn/ui generated
components in
`frontend/src/components/ui`, workflow-specific compositions in
`frontend/src/features/*`, and shared GradSync UI adapters in
`frontend/src/shared/ui`. Docker Compose defines backend, frontend, PostgreSQL,
Redis, worker, scheduler, file/media storage, SMTP/development email-capture,
and production-like static/media serving services.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Tailwind CSS + shadcn/ui added to existing React/Vite stack | Required to deliver a production-grade, accessible, token-driven operations interface while preserving React Router and TanStack Query architecture | Continuing ad hoc CSS and hand-rolled controls would preserve prototype interaction patterns, duplicate interaction behavior, and weaken accessibility consistency |
