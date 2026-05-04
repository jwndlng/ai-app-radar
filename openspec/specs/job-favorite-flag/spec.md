## Purpose

Backend support for marking jobs as favorites. Job records carry a `favorited` boolean field, and a toggle endpoint allows clients to flip that state.

## Requirements

### Requirement: Job records carry a favorited boolean
Job records in the store SHALL support a `favorited` field. Absence of the field SHALL be treated as `false`.

#### Scenario: New job has no favorited field
- **WHEN** a job is created by the scout pipeline
- **THEN** the job record SHALL NOT contain a `favorited` field, and reads of that field SHALL be treated as `false`

### Requirement: Toggle endpoint flips favorited state
The system SHALL expose `PATCH /jobs/{job_id}/favorite` which toggles the `favorited` field on the job and persists the change.

#### Scenario: Toggle from unfavorited to favorited
- **WHEN** `PATCH /jobs/{job_id}/favorite` is called on a job where `favorited` is absent or `false`
- **THEN** the job's `favorited` field SHALL be set to `true`, saved, and the response SHALL contain `{"ok": true, "favorited": true}`

#### Scenario: Toggle from favorited to unfavorited
- **WHEN** `PATCH /jobs/{job_id}/favorite` is called on a job where `favorited` is `true`
- **THEN** the job's `favorited` field SHALL be set to `false`, saved, and the response SHALL contain `{"ok": true, "favorited": false}`

#### Scenario: Job not found
- **WHEN** `PATCH /jobs/{job_id}/favorite` is called with an unknown job ID
- **THEN** the endpoint SHALL return HTTP 404
