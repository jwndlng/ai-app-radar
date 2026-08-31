## Purpose

Specification for the FastAPI web application at `src/api/app.py` that exposes the job discovery pipeline as a REST API and serves the static frontend.

## Requirements

### Requirement: FastAPI application serves pipeline API and static frontend
The system SHALL provide a FastAPI application at `src/api/app.py` that mounts all pipeline routes under `/api` and serves static frontend files from `static/` at `/`. The app SHALL create the `static/` directory at startup if it does not exist.

#### Scenario: Static index served at root
- **WHEN** a GET request is made to `/`
- **THEN** the response serves `static/index.html` with status 200

#### Scenario: API and static coexist
- **WHEN** a GET request is made to `/api/jobs`
- **THEN** the JSON jobs response is returned, not a static file

### Requirement: Jobs listing endpoint
The system SHALL expose `GET /api/jobs` returning the full list of job records from `ApplicationStore` as JSON.

#### Scenario: Jobs returned successfully
- **WHEN** `GET /api/jobs` is called
- **THEN** the response has status 200 and body `{"jobs": [...], "total": N}` where each job includes at minimum `id`, `state`, `status`, `title`, and `company`

#### Scenario: Empty store returns empty list
- **WHEN** the JSON store is empty or absent
- **THEN** `GET /api/jobs` returns `{"jobs": [], "total": 0}` with status 200

### Requirement: Job stats endpoint
The system SHALL expose `GET /api/jobs/stats` returning per-state job counts (`total`, `discovered`, `parsed`, `match`, `review`, `applied`, `rejected`, `archived`, `failed`). The route SHALL be registered before the parameterized `GET /api/jobs/{job_id}` route so the literal path is not captured as a job ID.

#### Scenario: Stats returned successfully
- **WHEN** `GET /api/jobs/stats` is called
- **THEN** the response has status 200 with a count per state, computed via a database aggregation (not by loading all records)

#### Scenario: Stats path never shadowed by job detail
- **WHEN** `GET /api/jobs/stats` is called
- **THEN** the request SHALL NOT be routed to the job-detail handler with `job_id="stats"`

### Requirement: Bulk job editing
The system SHALL expose `POST /api/jobs/bulk` accepting `{"ids": [...], "action": "set_state"|"favorite"|"unfavorite"|"delete", "state"?: str, "reason"?: str}` and applying the action to every listed job in one request. `set_state` follows the single-job route's semantics (records `prev_state`; a rejection stamps `vetted_at` and stores the optional reason). Unknown IDs are reported in a `missing` list without failing the request; invalid actions or states return 400.

#### Scenario: Bulk rejection
- **WHEN** `POST /api/jobs/bulk` is called with `action: "set_state"`, `state: "rejected"`, and three IDs of which one does not exist
- **THEN** the two existing jobs are rejected with `prev_state`, `vetted_at`, and the reason recorded, and the response reports `updated: 2` with the unknown ID in `missing`

### Requirement: On-demand maintenance cleanup
The system SHALL expose `POST /api/maintenance/cleanup` that runs the job archiver with the configured thresholds and returns `{"ok": true, "archived": N}`.

#### Scenario: Cleanup archives old terminal and failed jobs
- **WHEN** `POST /api/maintenance/cleanup` is called and jobs qualify under `rejected_after_days` or `failed_after_days`
- **THEN** those jobs are moved to the archive file and removed from the active store, and the count is returned

### Requirement: Bulk undo by state preserves job data
The system SHALL expose `POST /api/jobs/undo-by-state` accepting `{"state": "<state>"}` that reverts every job in that state to its previous state. The operation SHALL load jobs with the full projection before saving them back, so no extended fields (description, sources, scores metadata, `prev_state`) are lost.

#### Scenario: Bulk undo keeps extended fields
- **WHEN** `POST /api/jobs/undo-by-state` is called for a state containing jobs with extended data fields
- **THEN** each reverted job SHALL retain all fields not explicitly stripped by the undo transition itself

### Requirement: Task registry tracks background operation status
The system SHALL maintain a `TaskRegistry` that records all pipeline operations and persists records to `artifacts/tasks.json`. Each task record SHALL include: `id` (8-char UUID prefix), `operation` (name of the operation), `status` (`running` / `done` / `failed`), `started_at`, `finished_at`, and `result` or `error`. The registry SHALL keep at most 100 records, dropping the oldest on overflow.

#### Scenario: Task created on operation trigger
- **WHEN** any POST pipeline endpoint is called
- **THEN** a task record is created with status `running` before the operation begins

#### Scenario: Task updated on completion
- **WHEN** a background pipeline operation finishes successfully
- **THEN** the task record status is updated to `done` and `finished_at` is set

#### Scenario: Task updated on failure
- **WHEN** a background pipeline operation raises an exception
- **THEN** the task record status is updated to `failed` and the error message is stored

#### Scenario: Task records persisted after each mutation
- **WHEN** a task is created, completed, or failed
- **THEN** the full registry is written to `artifacts/tasks.json` before the call returns

#### Scenario: Registry loads persisted records on startup
- **WHEN** the server starts and `artifacts/tasks.json` exists
- **THEN** the registry is pre-populated with the records from that file, preserving history across restarts

#### Scenario: Missing or corrupt file is a no-op at startup
- **WHEN** the server starts and `artifacts/tasks.json` is absent or contains invalid JSON
- **THEN** the registry starts empty and a warning is logged; the server starts successfully

### Requirement: Task listing endpoint
The system SHALL expose `GET /api/tasks` returning all task records ordered by `started_at` descending, as summary records: full event logs SHALL NOT be included (the endpoint is polled every 5 seconds). Running/cancelling tasks include at most their last 100 events; finished tasks include an empty `events` list. Every summary record carries an `event_count`. Stored events per task are capped at 500 (oldest dropped) to bound the record and the persisted `tasks.json`.

#### Scenario: Tasks returned
- **WHEN** `GET /api/tasks` is called
- **THEN** the response has status 200 and body `{"tasks": [...], "total": N}`

#### Scenario: Finished tasks ship no event log
- **WHEN** `GET /api/tasks` is called and a finished task has recorded events
- **THEN** its summary record has `events: []` and the full log remains available via `GET /api/tasks/{task_id}`

#### Scenario: Empty task list
- **WHEN** no operations have been run since server start
- **THEN** `GET /api/tasks` returns `{"tasks": [], "total": 0}`

### Requirement: Task detail endpoint
The system SHALL expose `GET /api/tasks/{task_id}` returning a single task record by ID.

#### Scenario: Known task returned
- **WHEN** `GET /api/tasks/abc12345` is called and the task exists
- **THEN** the response has status 200 with the full task record

#### Scenario: Unknown task returns 404
- **WHEN** `GET /api/tasks/notfound` is called and no task has that ID
- **THEN** the response has status 404

### Requirement: Scout all companies
The system SHALL expose `POST /api/scout` that starts the scout pipeline as a background task and returns a task ID immediately.

#### Scenario: Scout all returns task ID
- **WHEN** `POST /api/scout` is called
- **THEN** the response has status 200 with body `{"ok": true, "task_id": "<id>"}` and the scout pipeline runs in the background

#### Scenario: Scout all unknown company input is validated synchronously
- **WHEN** `POST /api/scout` is called with no body
- **THEN** the task is created and scout runs for all companies

### Requirement: Scout a single company
The system SHALL expose `POST /api/scout/{company_name}` that starts the scout pipeline for one company as a background task and returns a task ID immediately. If the company is not found, it SHALL return 404 synchronously before creating a task.

#### Scenario: Known company returns task ID
- **WHEN** `POST /api/scout/acme` is called and `acme` is a configured company
- **THEN** the response returns `{"ok": true, "task_id": "<id>"}` and the scout runs in the background

#### Scenario: Unknown company returns 404 synchronously
- **WHEN** `POST /api/scout/unknown-co` is called and the company is not configured
- **THEN** the response has status 404 with body `{"detail": "Company not found: unknown-co"}` and no task is created

### Requirement: Enrich a single job
The system SHALL expose `POST /api/enrich/{job_id}` that starts enrich for one job as a background task. If the job is not found, it SHALL return 404 synchronously.

#### Scenario: Job enrich returns task ID
- **WHEN** `POST /api/enrich/JOB-123` is called and the job exists
- **THEN** the response returns `{"ok": true, "task_id": "<id>"}` and enrich runs in the background

#### Scenario: Unknown job returns 404 synchronously
- **WHEN** `POST /api/enrich/NOTFOUND` is called and no job has that ID
- **THEN** the response has status 404 with body `{"detail": "Job not found: NOTFOUND"}` and no task is created

### Requirement: Enrich next N jobs
The system SHALL expose `POST /api/enrich/next` accepting a JSON body `{"limit": N}` that starts batch enrich as a background task and returns a task ID immediately.

#### Scenario: Enrich next N returns task ID
- **WHEN** `POST /api/enrich/next` is called with body `{"limit": 10}`
- **THEN** the response returns `{"ok": true, "task_id": "<id>"}` and up to 10 discovered jobs are enriched in the background

#### Scenario: Limit defaults to 10
- **WHEN** `POST /api/enrich/next` is called with body `{}`
- **THEN** up to 10 jobs are enriched in the background

### Requirement: Enrich all pending jobs
The system SHALL expose `POST /api/enrich/all` that starts enrich for all `discovered` jobs as a background task and returns a task ID immediately.

#### Scenario: Enrich all returns task ID
- **WHEN** `POST /api/enrich/all` is called
- **THEN** the response returns `{"ok": true, "task_id": "<id>"}` and all discovered jobs are enriched in the background

### Requirement: Evaluate a single job
The system SHALL expose `POST /api/evaluate/{job_id}` that starts evaluate for one job as a background task. If the job is not found, it SHALL return 404 synchronously.

#### Scenario: Job evaluate returns task ID
- **WHEN** `POST /api/evaluate/JOB-123` is called and the job exists
- **THEN** the response returns `{"ok": true, "task_id": "<id>"}` and evaluate runs in the background

#### Scenario: Unknown job returns 404 synchronously
- **WHEN** `POST /api/evaluate/NOTFOUND` is called and no job has that ID
- **THEN** the response has status 404 with body `{"detail": "Job not found: NOTFOUND"}` and no task is created

### Requirement: Evaluate next N jobs
The system SHALL expose `POST /api/evaluate/next` accepting a JSON body `{"limit": N}` that starts batch evaluate as a background task and returns a task ID immediately.

#### Scenario: Evaluate next N returns task ID
- **WHEN** `POST /api/evaluate/next` is called with body `{"limit": 10}`
- **THEN** the response returns `{"ok": true, "task_id": "<id>"}` and up to 10 parsed jobs are evaluated in the background

#### Scenario: Limit defaults to 10
- **WHEN** `POST /api/evaluate/next` is called with body `{}`
- **THEN** up to 10 jobs are evaluated in the background

### Requirement: Evaluate all pending jobs
The system SHALL expose `POST /api/evaluate/all` that starts evaluate for all `parsed` jobs as a background task and returns a task ID immediately.

#### Scenario: Evaluate all returns task ID
- **WHEN** `POST /api/evaluate/all` is called
- **THEN** the response returns `{"ok": true, "task_id": "<id>"}` and all parsed jobs are evaluated in the background

### Requirement: Run all remaining steps for a job
The system SHALL expose `POST /api/jobs/{job_id}/run` that starts all remaining pipeline steps for a job as a background task. If the job is not found, it SHALL return 404 synchronously.

#### Scenario: Run all returns task ID
- **WHEN** `POST /api/jobs/JOB-123/run` is called and the job exists
- **THEN** the response returns `{"ok": true, "task_id": "<id>"}` and remaining steps run in the background

#### Scenario: Unknown job returns 404 synchronously
- **WHEN** `POST /api/jobs/NOTFOUND/run` is called and no job has that ID
- **THEN** the response has status 404 with body `{"detail": "Job not found: NOTFOUND"}` and no task is created

### Requirement: Companies listing endpoint
The system SHALL expose `GET /api/companies` returning the full list of configured companies with their enabled state and metadata as JSON.

### Requirement: Company enabled-state mutation endpoint
The system SHALL expose `PATCH /api/companies/{company_name}` (or equivalent) accepting `{"enabled": true|false}` and persisting the enabled-state change to the company configuration.

### Requirement: Settings read endpoint
The system SHALL expose `GET /api/settings` returning the full current settings as a JSON object with all fields populated (defaults filled in for any absent file keys).

#### Scenario: Settings returned with defaults when file absent
- **WHEN** `GET /api/settings` is called and `configs/settings.yaml` does not exist
- **THEN** the response has status 200 and body contains all settings fields at their default values

#### Scenario: Settings returned with overrides from file
- **WHEN** `GET /api/settings` is called and `configs/settings.yaml` has `scout.respect_robots: false`
- **THEN** the response body contains `{"scout": {"respect_robots": false, ...other defaults...}, ...}`

### Requirement: Settings write endpoint
The system SHALL expose `PUT /api/settings` accepting a full settings JSON object and writing the editable sections (`scout`, `enrich`, `evaluate`, `archival`) to `configs/settings.yaml`. Sections not managed by the settings UI (notably `notifications`) SHALL be preserved from the existing file rather than overwritten. On success it SHALL return `{"ok": true}`.

#### Scenario: Settings saved successfully
- **WHEN** `PUT /api/settings` is called with a valid settings body
- **THEN** `configs/settings.yaml` is written with the provided values and the response is `{"ok": true}` with status 200

#### Scenario: Save preserves the notifications section
- **WHEN** `configs/settings.yaml` contains a `notifications.telegram` block and `PUT /api/settings` is called
- **THEN** the saved file SHALL still contain the original `notifications.telegram` block unchanged

#### Scenario: Subsequent GET reflects saved values
- **WHEN** `PUT /api/settings` is called with `{"scout": {"max_pages": 15}, ...}` followed by `GET /api/settings`
- **THEN** the GET response contains `scout.max_pages: 15`

### Requirement: Pipeline errors return structured error responses
When a background pipeline operation raises an exception, the error SHALL be captured in the task record (`status: failed`, `error: "<message>"`). The POST endpoint itself SHALL NOT return a 500 error for pipeline failures — only for request-level errors (e.g. missing body field).

#### Scenario: Pipeline failure captured in task record
- **WHEN** a background scout operation raises an exception
- **THEN** the task record is updated with `status: failed` and the exception message, and the POST response was already `{"ok": true, "task_id": "..."}` with status 200

#### Scenario: Request-level error still returns 500
- **WHEN** a POST endpoint receives a malformed request body
- **THEN** the response has status 422 or 500 with an error detail
