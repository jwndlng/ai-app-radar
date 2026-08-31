# job-query-projections Specification

## Purpose
TBD - created by archiving change frontend-query-optimization. Update Purpose after archive.
## Requirements
### Requirement: Summary and Full Query Projections
The database provider and repository SHALL support a `projection` parameter (`summary` or `full`) on `list_jobs`.

#### Scenario: Summary projection excludes heavy text blobs
- **WHEN** `list_jobs` is called with `projection="summary"`
- **THEN** returned records SHALL contain card-level metadata (`id`, `company`, `title`, `url`, `location`, `state`, `status`, `final_score`, `location_score`, `seniority_score`, `favorited`, `discovered_at`, `updated_at`, `vetted_at`, `archived_at`, `error_message`) and SHALL omit large unstructured text fields (`description`, `key_responsibilities`, `required_qualifications`, `reasons`).

#### Scenario: Summary projection includes card-rendered data fields
- **WHEN** `list_jobs` is called with `projection="summary"`
- **THEN** returned records SHALL also include `score`, `salary_range`, and `compensation_score` (extracted from the data payload), because collapsed job cards render them without fetching the full record.

#### Scenario: Summary records must not be saved back
- **WHEN** a caller mutates records obtained with `projection="summary"` and intends to persist them
- **THEN** the caller SHALL re-fetch with `projection="full"` before saving, because upserting a summary record rewrites the job's data payload from the projected dict and destroys all omitted fields.

#### Scenario: Full projection includes all payload data
- **WHEN** `list_jobs` is called with `projection="full"`
- **THEN** returned records SHALL include all deserialized JSON fields.

### Requirement: Single-Job Detail Route
The API SHALL provide `GET /api/jobs/{job_id}` returning the complete job record with all fields.

#### Scenario: Fetching existing job detail
- **WHEN** a client sends `GET /api/jobs/{job_id}` for an existing job
- **THEN** the server SHALL return `200 OK` with the complete job dictionary including full descriptions and evaluation reasons.

#### Scenario: Fetching non-existent job detail
- **WHEN** a client sends `GET /api/jobs/{job_id}` for an invalid job ID
- **THEN** the server SHALL return `404 Not Found`.

### Requirement: Server-Side Query Filtering and Sorting
The `list_jobs` method and `GET /api/jobs` endpoint SHALL support server-side filtering by `state`, `status`, `search`, `favorites_only`, and ordering by `sort_by` and `sort_order`.

#### Scenario: Filtering by state and search keyword
- **WHEN** `GET /api/jobs?state=match&search=security` is requested
- **THEN** only matching jobs with `state="match"` and title/company/location containing "security" SHALL be returned.

#### Scenario: Offset applies with or without a limit
- **WHEN** `list_jobs` is called with `offset=N` and no `limit`
- **THEN** the first N records SHALL still be skipped (offset SHALL NOT be silently ignored when `limit` is absent).

