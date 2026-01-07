## [0.2.0] - 2026-01-07

### Added
- Standardized API error format and domain errors:
  - JSON error body shape: `{ "error": { "code", "message", "details?" }, "request_id" }`.
  - New domain error types: `RECORD_NOT_FOUND` (404), `CONFLICT`/`ALREADY_PROCESSED` (409), `VALIDATION_ERROR` (422), `INTERNAL_ERROR` (500).
- Global exception handlers:
  - Converts domain, validation, and unexpected exceptions into consistent JSON responses and sets `X-Request-ID` in responses.
- Request-scoped middleware and structured request logging:
  - Accepts `X-Request-ID` (or generates one), records `method`, `path`, `status`, `duration_ms`, and `request_id` as structured log lines.
- Operational health check:
  - `/health` now returns service status, version, and a basic DB connectivity check.
- Structured processing logs:
  - Processing emits structured events for transitions and failures (`record_id`, `old_status`, `new_status`, error details).
- Tests:
  - New tests covering failure modes: missing record → 404, re-processing conflict → 409, invalid payload → 422, and report summary on an empty DB.
- Repo polish:
  - Added `.env.example` and README documentation describing the error schema, state model, and example curl commands.

### Changed
- Removed top-level `app/` shim package and migrated imports to `workflow_service.app.*`.
- Defensive test / DB improvements (engine disposal before reset where necessary; reporting counts made defensive).

### Fixed
- Prevent exposing raw tracebacks to clients — unexpected errors return a safe, generic `INTERNAL_ERROR` response while full stack traces are logged server-side.

### Migration / Compatibility notes
- If your code or tooling imported from the removed top-level `app.*` shims, update imports to `workflow_service.app.*`.
- Clients can now rely on `X-Request-ID` response header and the `request_id` field in error bodies for log correlation.

### QA checklist
- [ ] CI for `day6-prod-shape` passes.
- [ ] Deploy to staging and verify:
  - `GET /health` returns `service: ok` and `database: status: ok`.
  - Create a record (POST `/records`) → 201.
  - Process a pending record (POST `/records/{id}/process`) → processed; logs show `status_transition`.
  - Re-process a processed record → 409 with structured error and `request_id`.
  - POST invalid payload → 422 with `VALIDATION_ERROR` and `request_id`.
  - `GET /reports/summary` on an empty DB returns zero totals.
- [ ] Verify logs include `request_id` on all request-related entries for easy correlation.

### References
- Branch / PR: `day6-prod-shape` (see PR for full diff)
