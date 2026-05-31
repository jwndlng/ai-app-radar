# Spec: pipeline-run-all

## Purpose

Defines the behaviour of the `POST /pipeline/all` endpoint, which triggers a full pipeline run (scout → enrich → evaluate) as a single background task.

## Requirements

### Requirement: POST /pipeline/all endpoint exists
The API SHALL expose a `POST /pipeline/all` endpoint that starts a full pipeline run (scout → enrich → evaluate) as a single background task and returns immediately with a `task_id`.

#### Scenario: Endpoint accepts request and returns task ID
- **WHEN** a client sends `POST /pipeline/all`
- **THEN** the response is `{"ok": true, "task_id": "<id>"}` with HTTP 200, and the pipeline begins running in the background

### Requirement: Stages run in fixed sequence
The endpoint SHALL execute the three pipeline stages in strict order: scout first, then enrich, then evaluate. A subsequent stage SHALL NOT start before the preceding stage has fully completed.

#### Scenario: Enrich runs only after scout finishes
- **WHEN** the run-all task is active and scout has completed
- **THEN** enrich begins processing jobs discovered in that scout run before evaluate is started

#### Scenario: Evaluate runs only after enrich finishes
- **WHEN** enrich has completed in a run-all task
- **THEN** evaluate begins scoring enriched jobs

### Requirement: Task is cancellable between stages
The task created by `POST /pipeline/all` SHALL be cancellable via `DELETE /tasks/<task_id>`. A cancel request SHALL be honoured at the next stage boundary — the current stage completes normally and the following stage does not start. Cancellation SHALL also propagate into the active stage's own cancellation checkpoint.

#### Scenario: Cancel during scout stops before enrich
- **WHEN** a cancel is issued while scout is running
- **THEN** scout finishes its current checkpoint, enrich does not start, and the task status transitions to `cancelled`

#### Scenario: Cancel during enrich stops before evaluate
- **WHEN** a cancel is issued while enrich is running
- **THEN** enrich finishes its current checkpoint, evaluate does not start, and the task status transitions to `cancelled`

### Requirement: Progress and events are reported through the task record
The run-all task SHALL emit `on_progress` and `on_event` callbacks for each stage. Progress SHALL reflect the current stage's `(current, total)` and MAY reset to `(0, total)` at each stage boundary.

#### Scenario: Progress updates are visible on the task record
- **WHEN** a stage is actively processing items
- **THEN** `GET /tasks/<task_id>` returns a `progress_current` and `progress_total` reflecting that stage's progress

#### Scenario: Events from all three stages appear on the task
- **WHEN** the run-all task completes
- **THEN** the task record's `events` list contains events emitted by scout, enrich, and evaluate

### Requirement: Task status reflects full pipeline outcome
The task status SHALL be `done` only if all three stages complete without error. If any stage raises an unhandled exception the task status SHALL be `failed` and subsequent stages SHALL NOT run.

#### Scenario: All stages succeed
- **WHEN** scout, enrich, and evaluate all complete without error
- **THEN** the task status is `done`

#### Scenario: Stage failure stops the pipeline
- **WHEN** enrich raises an unhandled exception during a run-all task
- **THEN** evaluate does not run and the task status is `failed`
