## Purpose

Specification for permanently removing a job from the pipeline via the API and the frontend dashboard.

## Requirements

### Requirement: Delete job endpoint
The system SHALL expose `DELETE /api/jobs/{job_id}` that permanently removes the matching job from `ApplicationStore`. The job is identified by its `id` field. If no job with that ID exists, the endpoint SHALL return 404. On success it SHALL return 200 with `{"ok": true, "id": "<job_id>"}`.

#### Scenario: Job deleted successfully
- **WHEN** `DELETE /api/jobs/abc12345` is called and a job with `id: "abc12345"` exists
- **THEN** the response is 200 with `{"ok": true, "id": "abc12345"}` and the job is absent from subsequent `GET /api/jobs` responses

#### Scenario: Job not found
- **WHEN** `DELETE /api/jobs/nonexistent` is called and no job has that ID
- **THEN** the response is 404 with `{"detail": "Job not found"}`

#### Scenario: Store persisted after deletion
- **WHEN** a job is successfully deleted
- **THEN** `applications.json` is written immediately so the deletion survives a server restart

### Requirement: Dashboard delete button with confirmation
The frontend dashboard SHALL render a delete button on each job card. Clicking the button once SHALL enter an armed state (visual indicator); clicking again SHALL call `DELETE /api/jobs/{id}` and remove the card from the UI. Clicking anywhere outside the armed button SHALL disarm it without deleting.

#### Scenario: Button arms on first click
- **WHEN** the user clicks the delete button on a job card
- **THEN** the button visually changes to a confirmation state (e.g. turns red, label changes to "Confirm?")

#### Scenario: Second click deletes
- **WHEN** the button is armed and the user clicks it again
- **THEN** `DELETE /api/jobs/{id}` is called and the card is removed from the list on success

#### Scenario: Click outside disarms
- **WHEN** the button is armed and the user clicks anywhere outside it
- **THEN** the button returns to its default state without making a delete request

#### Scenario: Delete failure shown
- **WHEN** the delete API call returns a non-2xx response
- **THEN** the card remains visible and a brief error indicator is shown on the button
