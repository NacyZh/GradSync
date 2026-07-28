# US3 Structured Reports Checkpoint

- [x] Seven controlled bilingual field types validate; published versions are immutable.
- [x] Reporting periods lock one published template and scheduler opening is idempotent.
- [x] Typed required/numeric/source responses and returned-report resubmission pass.
- [x] Legacy narrative and review fields remain queryable with additive schema.
- [x] Analytics enforce 104 periods, explicit missing values, source report IDs, and no ranking/score.
- [x] CSV export uses the same authorized bounded aggregate.
- [x] Reports expose Periods, History, Template, and Analytics views with global toast feedback.
- [x] Backend unit/contract/integration and frontend component/E2E checkpoints pass.

Evidence recorded 2026-07-28:

- Backend focused suites: 10 tests passed across template, period, response,
  analytics, contract, revision, migration, and range coverage.
- Frontend structured-report components: 2 tests passed.
- Playwright structured-report journey: 1 test passed.
- Strict OpenAPI: 41 feature operations covered.
