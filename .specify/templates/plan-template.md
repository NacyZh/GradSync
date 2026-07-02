# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. The
feature specification MUST exist first. Technology stack, frameworks,
middleware, and database choices are defined here for this feature.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Reliability/Operations Goals**: [health/readiness, queue timing, backup/restore, rollback, observability, or N/A]

**Security/Compliance Constraints**: [auth, authorization, data isolation, secrets, transport, audit, or N/A]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

**Deployment/Monitoring/Degradation**: [deployment topology, health/readiness,
metrics, alerts, fallback/degradation behavior for new dependencies, or N/A]

**Data Migration & Rollback**: [schema/data migration, rollback approach,
backup/restore impact, or N/A]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **SDD Order**: Confirm `spec.md` exists, includes the five mandatory modules,
  records included and excluded scope, and has no unresolved clarification that
  blocks planning.
- **Review Readiness**: Confirm product, testing, and development review status
  is recorded in the specification, or record a release-blocking risk.
- **Required Plan Artifacts**: Confirm this plan will produce/update
  `plan.md`, `research.md`, `data-model.md`, and `contracts/openapi.yaml` or
  `.json` when interfaces exist.
- **Technology Governance**: List each new framework, middleware, database,
  storage service, queue, or external integration and identify the
  `research.md` comparison that justifies it. Heavy dependencies without
  rationale fail this gate.
- **Layering and Code Baselines**: Identify access, business, data, and shared
  core layer ownership. Confirm naming, configuration, validation, documentation
  comments, reuse, and backward-compatible change expectations.
- **TDD/Test Plan**: Define tests that must be written before implementation by
  level (unit, contract, integration, end-to-end, readiness/smoke) and map them
  to AC IDs, edge cases, security boundaries, data changes, concurrency, or
  operations. Any test gap must include reason, owner, expiry date, and release
  risk.
- **Security Gate**: Confirm authentication, authorization, injection/XSS
  protection, sensitive data handling, log masking, upload validation,
  rate-limiting, circuit-breaking, degradation, and audit needs.
- **Performance Gate**: Confirm pagination, batch limits, cache strategy,
  indexing, long-transaction avoidance, and measurable thresholds.
- **Deployment/Operations Gate**: Record deployment topology impact, new
  environment variables/secrets, monitoring and alert signals, backup/restore
  impact, migration and rollback plan, release checks, and manual operator
  steps.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── openapi.yaml     # Required when frontend/backend or service APIs exist
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Required Design Artifact Checklist

- [ ] `research.md` records dependency research, performance/security risk
  assessment, and technology choice comparisons.
- [ ] `data-model.md` records entities, fields, constraints, indexes,
  relationships, and migration approach.
- [ ] `contracts/openapi.yaml` or `.json` records external API contracts when
  interfaces exist.
- [ ] `quickstart.md` records runnable validation scenarios aligned to AC IDs.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
