# Specification: Task Cancellation

## Purpose

TBD — Allows users to cancel a running background task via the API and UI, transitioning it through `cancelling` to `cancelled` while preserving any partial results already produced.

## Requirements

### Requirement: Running tasks can be cancelled via the API
The API SHALL expose `DELETE /api/tasks/{task_id}` to request cancellation of a running task. If the task is in `running` status, its status SHALL immediately transition to `cancelling` and the runtime SHALL be signalled to stop picking up new items. If the task is already `done`, `failed`, or `cancelled`, the endpoint SHALL return 409 Conflict.

#### Scenario: Cancel a running task
- **WHEN** `DELETE /api/tasks/{task_id}` is called and the task status is `running`
- **THEN** the response is `200 OK` with `{"ok": true}` and the task status transitions to `cancelling`

#### Scenario: Cancel an already-finished task
- **WHEN** `DELETE /api/tasks/{task_id}` is called and the task status is `done`, `failed`, or `cancelled`
- **THEN** the response is `409 Conflict`

#### Scenario: Cancel a non-existent task
- **WHEN** `DELETE /api/tasks/{task_id}` is called for an unknown task ID
- **THEN** the response is `404 Not Found`

### Requirement: TaskRecord supports cancelling and cancelled statuses
`TaskRecord.status` SHALL accept the values `cancelling` (cancellation requested, runtime is draining in-flight items) and `cancelled` (runtime has fully stopped). These statuses SHALL be persisted to the task history file alongside `running`, `done`, and `failed`.

#### Scenario: Task transitions cancelling → cancelled
- **WHEN** a task in `cancelling` status has its remaining in-flight items finish
- **THEN** the task status transitions to `cancelled` and `finished_at` is set

#### Scenario: Cancelled task appears in task history
- **WHEN** a task has been cancelled and the page is reloaded
- **THEN** the task appears in the tasks panel with status `cancelled`

### Requirement: Partial results from a cancelled task are preserved
Items already processed by the runtime before cancellation was requested SHALL be retained in the application store. The cancellation SHALL only prevent new items from being started; it SHALL NOT roll back completed work.

#### Scenario: Partial scout results kept after cancel
- **WHEN** a Scout task has discovered 5 jobs and is then cancelled before processing all companies
- **THEN** the 5 already-discovered jobs remain in the store after cancellation

### Requirement: UI task cards show a cancel button for running tasks
Each task card in the tasks panel that has status `running` or `cancelling` SHALL display a cancel button (×). Clicking it SHALL call `DELETE /api/tasks/{task_id}`. While the task is in `cancelling` status, the button SHALL be disabled and the card SHALL show a `cancelling…` indicator. Once `cancelled`, the card shows a `cancelled` badge.

#### Scenario: Cancel button visible on running task
- **WHEN** a task card is rendered with status `running`
- **THEN** a cancel (×) button is visible on the card

#### Scenario: Cancel button triggers API call
- **WHEN** the user clicks the cancel button on a running task card
- **THEN** `DELETE /api/tasks/{task_id}` is called and the card transitions to `cancelling` state

#### Scenario: Cancelling state shown while draining
- **WHEN** a task is in `cancelling` status
- **THEN** the task card shows a `cancelling…` indicator and the cancel button is disabled

#### Scenario: Cancelled badge shown on completed cancellation
- **WHEN** a task transitions to `cancelled` status
- **THEN** the task card displays a `cancelled` status badge
