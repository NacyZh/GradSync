<!--
Sync Impact Report
Version change: 1.1.0 -> 2.0.0
Modified principles:
- I. Production-Grade Code Quality -> I. SDD-First Development Workflow
- II. Tests Prove Releasability -> II. Requirements and Specification Standards
- III. Operable User Experience -> III. Plan and Technology Governance
- IV. Measured Performance and Reliability -> IV. Task Decomposition and Traceability
- V. Secure, Observable, Maintainable Architecture -> V. Universal Coding, Testing, Security, and Performance Baselines
Added sections:
- Git and Branch Collaboration Rules
- CI/CD Gate Rules
- Documentation Rules
Removed sections:
- Production Readiness Gates
Templates requiring updates:
- ✅ .specify/templates/plan-template.md
- ✅ .specify/templates/spec-template.md
- ✅ .specify/templates/tasks-template.md
- ✅ .specify/templates/commands/*.md (directory not present)
Runtime guidance reviewed:
- ✅ README.md
- ✅ AGENTS.md
- ✅ docs/production.md
Follow-up TODOs:
- None
-->
# GradSync Constitution

This constitution is the global mandatory constraint set for Spec-Kit SDD
specification-driven development in GradSync. All `/speckit.*` commands, AI code
generation, manual development, and CI validation MUST comply. No feature,
defect fix, refactor, or release change is exempt.

## Core Principles

### I. SDD-First Development Workflow
All new features, iterative changes, defect fixes, and business behavior
changes MUST follow this order: write or update the relevant `spec.md`, produce
or refresh the implementation `plan.md` and design artifacts, then implement
code. Business code MUST NOT be written before the corresponding specification
and plan exist.

The single source of truth is the `specs/` directory. Code, APIs, tests, CI
checks, and documentation MUST align with the acceptance criteria in the
applicable specification. Any requirement change or logic adjustment MUST update
the relevant specification first and then regenerate or amend downstream plan,
tasks, contracts, tests, and implementation. Direct code-only business changes
are prohibited.

TDD is mandatory. Before generating or writing business implementation code,
unit, integration, contract, or end-to-end tests appropriate to the change MUST
be produced and must fail for the missing behavior unless the plan records an
explicit approved exception. Scope MUST be controlled in each specification by
stating included capabilities and excluded/non-goal capabilities.

Rationale: GradSync must keep business intent, generated code, human code,
tests, and release validation aligned through a reviewable SDD chain.

### II. Requirements and Specification Standards
Every feature folder's `spec.md` MUST contain five complete modules:

1. Business background, user roles, and core goals.
2. Complete positive business flows.
3. Full exception, boundary, and degradation scenarios.
4. Quantifiable and automatable acceptance criteria.
5. Dependencies, external systems, business assumptions, and unsupported
   capabilities for the current scope.

The specification MUST define independently testable user journeys, measurable
success criteria, important edge cases, security and privacy boundaries, and
scope exclusions. Ambiguous questions MUST be recorded in the specification
appendix or clarification section, and the clarification loop MUST be closed
before entering the plan phase.

Rationale: Specifications must be complete enough to drive implementation and
CI validation without relying on hidden oral context.

### III. Plan and Technology Governance
Executing `/speckit-plan` MUST produce or update all required design artifacts:

1. `plan.md`: architecture, module boundaries, feature-specific technology
   choices, deployment approach, risks, dependencies, and trade-off rationale.
2. `data-model.md`: entities, field constraints, indexes, relationships, and
   migration approach.
3. `contracts/openapi.yaml` or `contracts/openapi.json`: frontend/backend or
   service API contracts when interfaces exist.
4. `research.md`: third-party dependency research, performance and security
   risk assessment, and technology comparisons.

Concrete technology stacks, frameworks, middleware, and database choices are
defined inside the current feature's `plan.md`. All technology choices MUST have
research-backed comparison notes in `research.md`; heavy dependencies MUST NOT
be introduced without a documented reason. Choices MUST account for
maintainability, operational cost, and the team's existing capabilities.

Any new middleware, database, storage service, queue, framework, or external
service MUST include deployment, monitoring, failure-degradation, rollback, and
secret/configuration handling in the plan. Plans MUST fail the Constitution
Check if these concerns are absent.

Rationale: Technical decisions must be local to the feature plan but governed by
consistent evidence, maintainability, and operations requirements.

### IV. Task Decomposition and Traceability
`tasks.md` MUST decompose work into tasks that each fit within 8 hours of
development effort. Larger tasks MUST be split before implementation begins.

Every task MUST trace to one or more specification acceptance criteria or
explicit plan gates and include a self-check expectation. Tasks MUST identify
dependencies, parallel or serial execution order, and ownership area such as
frontend, backend, test, documentation, operations, or CI. Test tasks MUST appear
before implementation tasks for the behavior they prove.

Implementation MUST stop at each story checkpoint until the story is
independently testable against its acceptance criteria. Tasks that cannot be
tested independently MUST state the dependency and risk in `tasks.md`.

Rationale: Fine-grained, traceable tasks make SDD executable by AI agents and
human reviewers while preserving TDD order.

### V. Universal Coding, Testing, Security, and Performance Baselines
All implementation, regardless of language or framework, MUST isolate
responsibilities across:

- Access layer: external requests, parameter intake, routing, and dispatch.
- Business layer: core business logic and workflow orchestration.
- Data layer: persistence, cache, and external service calls.
- Shared core layer: common utilities, authorization, logging, exceptions,
  constants, and reusable cross-cutting behavior.

Code MUST use semantic naming, plan-defined style conventions, configuration or
environment injection for secrets/addresses, validation for all external input,
single-responsibility functions, documentation comments for public interfaces,
data entities, and core functions, shared utilities for repeated logic, and
extension-compatible changes that do not casually remove old fields or
interfaces. Code MUST be productional level, NOT demo.

Tests MUST cover core business logic with unit tests, external interfaces and
critical flows with integration or contract tests, and normal, exceptional,
boundary, and concurrency scenarios where relevant. Test environments MUST be
isolated and MUST NOT operate on production resources.

Security is mandatory for every feature. External interfaces MUST enforce
authentication and role/permission checks. Implementations MUST protect against
SQL injection, XSS, privilege escalation, replay attacks, unsafe uploads, and
secret leakage. Sensitive data MUST be encrypted where required, transported
over encrypted channels, and masked in logs. File uploads MUST validate type,
size, path, and executable-risk constraints. Open interfaces MUST include
rate-limiting, circuit-breaking, or degradation strategies when exposed to abuse
or dependency failure.

Performance baselines apply globally. Large lists MUST be paginated; batch
interfaces MUST limit single-request volume; hot data SHOULD use an explicit
cache strategy when justified by the plan; large database tables MUST have
reasonable indexes; batch operations MUST be chunked to avoid long transactions
and blocking.

Rationale: These engineering baselines are independent of the selected stack and
must hold for all GradSync code.

## Git and Branch Collaboration Rules

Branches MUST follow `spec/feature-{spec-id}` for feature work unless the
repository's hosting workflow requires an equivalent naming convention. One
specification MUST map to one independent branch.

Commits MUST use `[{spec-id}] 描述变更内容`, for example
`[005] 完成用户登录接口实现`. Pull requests MUST include the relevant
specification documents, plan artifacts, code, and tests. A PR that changes
business behavior without a corresponding spec and plan update MUST be blocked.

## CI/CD Gate Rules

CI MUST validate specification directory completeness, code style, formatting,
unit tests, integration/contract tests required by the plan, and release
readiness checks before merge. Missing acceptance criteria, missing tests,
business-code changes without a corresponding specification, or spec/code logic
drift MUST block the merge.

CI/CD pipelines MUST prevent generated runtime/build artifacts from remaining in
source scope and MUST reject unsafe configuration defaults for production.
Production release gates MUST include smoke, readiness, security, migration, and
rollback checks required by the current plan.

## Documentation Rules

Interfaces, data models, scheduled jobs, third-party integrations, deployment
assumptions, and major architecture or technology decisions MUST be documented.
Requirement or logic changes MUST update the corresponding `spec.md`,
OpenAPI/interface contract, and relevant design artifacts. The project root
README MUST record common local startup, environment, and test commands.
Significant architecture and technology changes MUST be recorded in
`research.md` with comparison and rationale.

## Development Workflow

Feature specifications MUST be created or updated before plans. Plans MUST
translate specifications into architecture, data model, contracts, research,
deployment impact, security controls, tests, observability, migration, rollback,
and release validation. Tasks MUST convert the plan into traceable, test-first,
8-hour-or-less work units. Implementation MUST follow tasks in dependency order
and mark completed tasks only after validation passes.

Reviewers MUST block changes that bypass the SDD order, lack required
stakeholder review, miss tests, weaken security, omit operational visibility,
introduce unjustified dependencies, skip migration or rollback planning, ignore
performance baselines, or leave scope boundaries unclear.

## Governance

This constitution supersedes conflicting development practices for GradSync.
Amendments require a documented update to this file, a Sync Impact Report, and
updates to affected Spec Kit templates or runtime guidance in the same change.

Versioning follows semantic versioning:

- MAJOR for backward-incompatible governance changes, principle replacements,
  or removed/redefined required workflows.
- MINOR for new principles, new required sections, or materially expanded gates
  that preserve existing workflow semantics.
- PATCH for clarifications, wording fixes, typo fixes, or non-semantic
  refinements.

Every generated specification, plan, task list, implementation, and CI workflow
MUST be checked against the current constitution. Compliance exceptions MUST be
explicit, time-bounded, owned, reviewed, and represented in the relevant plan
before release.

**Version**: 2.0.0 | **Ratified**: 2026-06-25 | **Last Amended**: 2026-07-02
