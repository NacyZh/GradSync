# Implementation Plan: Research Group Operations

**Branch**: `001-research-group-ops` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-research-group-ops/spec.md`

## Summary

Build GradSync as a web application for graduate research group operations.
Advisors manage project membership and hierarchical task plans, students submit
versioned drafts and weekly progress reports, advisors review submissions with
inline comments, project records remain strictly isolated by project membership,
lab resources are booked without conflicts, and email reminders cover pending
reviews, approaching deadlines, and new submissions.

The implementation uses Django for backend domain logic and project-scoped
authorization, React with TypeScript and Vite for the web application,
PostgreSQL for durable relational records, Redis for background job coordination
and transient state, and Docker Compose for local and deployment orchestration.

## Technical Context

**Language/Version**: Python 3.12 for Django backend; TypeScript 5.x for React
web frontend

**Primary Dependencies**: Django 5.x, Django REST Framework, Celery, django-celery-beat,
django-celery-results, Redis client, PostgreSQL driver, React 18, Vite 5,
React Router, TanStack Query, React Hook Form, Zod, Vitest, Playwright,
pytest, pytest-django

**Frontend Scope Decision**: This feature keeps the approved React/Vite/TanStack
Query stack. Requested paper-library, code-repository, PDF/DOI/BibTeX,
WebSocket, Tailwind/shadcn, Redux Toolkit, and RTK Query capabilities are
tracked as follow-up scope rather than being introduced into this feature's
implementation plan.

**Storage**: PostgreSQL for users, projects, memberships, tasks, draft versions,
reports, inline comments, bookings, notifications, and audit records; Redis for
Celery broker, reminder scheduling coordination, cache, and short-lived locks

**Testing**: pytest and pytest-django for backend unit, contract, and integration
tests; Vitest and React Testing Library for frontend unit/component tests;
Playwright for end-to-end project isolation, submission review, and booking
flows; contract tests against `contracts/openapi.yaml`

**Target Platform**: Docker Compose-managed web deployment with backend API,
frontend web app, PostgreSQL, Redis, and worker services

**Project Type**: Web application with Django backend and React/Vite frontend

**Performance Goals**: Project dashboard opens within 3 seconds for projects
with up to 500 active records; project-scoped search/filter completes within 2
seconds; visible confirmation for common record updates appears within 2
seconds; eligible reminder emails are queued or recorded within 5 minutes

**Constraints**: Strict project isolation for all tasks, drafts, reports,
comments, bookings, notifications, and activity; no cross-project record
linking except through explicit membership in each project; overlapping lab
resource bookings must be prevented; archived projects are read-only unless
reopened; all behavioral changes require automated tests

**Scale/Scope**: At least 50 active projects, 500 total project members, and
500 active records per project for the specified user journeys

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code Quality**: PASS. Backend modules will be separated by domain
  responsibility (`projects`, `tasks`, `submissions`, `resources`,
  `notifications`, `audit`) with shared project-scope permission helpers.
  Frontend modules will mirror user workflows (`project dashboard`, `task tree`,
  `draft review`, `weekly reports`, `resource booking`, `notifications`) and use
  typed contracts generated or checked from the OpenAPI document. Non-obvious
  isolation and booking conflict rules will be documented in domain services.
- **Testing**: PASS. Required coverage includes backend unit tests for hierarchy
  and state rules, contract tests for every public API operation, integration
  tests for project isolation and booking conflicts, frontend component tests
  for critical forms and states, and Playwright flows for advisor/student
  end-to-end journeys. No test gaps are approved.
- **User Experience**: PASS. Project context must remain visible on every
  project-scoped route. The web app will include advisor project management,
  student assigned work, review queues, and booking views with consistent
  navigation, keyboard support, labels, and loading/empty/error states.
- **Performance**: PASS. Performance requirements from the spec are carried into
  backend query design, frontend data loading, and quickstart validation. Search
  and dashboard views will be measured with seeded projects at target scale.
- **Architecture**: PASS. Django, React/Vite, PostgreSQL, Redis, and Docker
  Compose are user-selected stack choices and fit the web app scope. Celery is
  justified for reliable email and reminder processing outside request flows.

**Post-Design Re-check**: PASS. `research.md`, `data-model.md`,
`contracts/openapi.yaml`, and `quickstart.md` preserve the same gates. Project
isolation is modeled as explicit membership plus project foreign keys on every
research record. Booking conflict prevention and notification delivery are
captured as contracts and validation scenarios.

## Project Structure

### Documentation (this feature)

```text
specs/001-research-group-ops/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
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
│   ├── notifications/
│   └── audit/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

frontend/
├── package.json
├── vite.config.ts
├── src/
│   ├── app/
│   ├── routes/
│   ├── features/
│   │   ├── projects/
│   │   ├── tasks/
│   │   ├── submissions/
│   │   ├── resources/
│   │   └── notifications/
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
isolation, version history, booking conflicts, and notification scheduling in
backend domain services, while the frontend owns workflow presentation and
client-side validation. Docker Compose defines backend, frontend, PostgreSQL,
Redis, worker, scheduler, and email-capture services.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
