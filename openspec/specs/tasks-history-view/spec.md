# Specification: Tasks History View

## Purpose

To provide a dedicated Tasks view that displays all retained background operation records, giving users full visibility into pipeline activity history.

## Requirements

### Requirement: Tasks view displays all retained task records
The Tasks view SHALL display all records held by `TaskRegistry` (up to 100), ordered newest-first, fetched from `GET /api/tasks`. The view SHALL be accessible via a "Tasks" tab in the top navigation bar at all times, regardless of whether any task is currently running.

#### Scenario: Tasks view loads on tab click
- **WHEN** the user clicks the "Tasks" nav tab
- **THEN** `currentView` is set to `'tasks'` and the Tasks view is rendered with all records from `GET /api/tasks`

#### Scenario: All records shown, not just recent
- **WHEN** the Tasks view is open and a task finished more than 2 minutes ago
- **THEN** that task record is still visible in the list

#### Scenario: Empty state when no tasks have run
- **WHEN** `GET /api/tasks` returns an empty list
- **THEN** the Tasks view displays a message indicating no tasks have run yet

### Requirement: Task row displays operation, status, and timing
Each task row in the Tasks view SHALL display: the formatted operation name, a status indicator (running / done / failed), the start time, and the elapsed time or duration. Rows SHALL reuse the existing `task-item`, `task-dot`, and `task-events` CSS classes.

#### Scenario: Running task shows live elapsed time
- **WHEN** a task has `status === 'running'`
- **THEN** the row shows a pulsing indicator and a live-updating elapsed time

#### Scenario: Completed task shows duration
- **WHEN** a task has `status === 'done'`
- **THEN** the row shows a green indicator and the total duration (finished_at − started_at)

#### Scenario: Failed task shows error indicator
- **WHEN** a task has `status === 'failed'`
- **THEN** the row shows a red indicator and the error is accessible in the events log
