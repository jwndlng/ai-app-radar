## Purpose

Specification for the Alpine.js single-page application frontend served from `static/index.html`. The SPA provides a live interface for browsing jobs and triggering pipeline operations, with real-time task status via background polling.

## Requirements

### Requirement: SPA loads and displays jobs on page load
The frontend SHALL be a single-page application served from `static/index.html` using Alpine.js (CDN). On load it SHALL fetch `GET /api/jobs` and render the job list without a full page reload.

#### Scenario: Page load fetches jobs
- **WHEN** the user opens the app in a browser
- **THEN** `GET /api/jobs` is called automatically and jobs are rendered in the job list

#### Scenario: Empty job list shown gracefully
- **WHEN** `GET /api/jobs` returns zero jobs
- **THEN** an empty-state message is displayed instead of a blank list

### Requirement: Top action bar for bulk pipeline operations
The frontend SHALL display a persistent pipeline action area with three
stage cards (Scout, Enrich, Evaluate) laid out as named CSS classes
(not inline styles). Each card SHALL display a pending-job count badge
showing how many jobs are queued for that stage; the badge SHALL be
hidden when the count is zero. Scout SHALL have a company selector
dropdown and a limit dropdown (shown when "All companies" is selected).
Enrich and Evaluate SHALL each have a limit dropdown (All, 5, 10, 50).
A secondary actions row SHALL appear below the stage cards, visually
separated by a divider, and SHALL contain the Undo all control.

#### Scenario: Scout all triggered
- **WHEN** the scout company selector is set to "All companies" and the Run button is clicked
- **THEN** `POST /api/scout` is called and the new task appears in the Running Tasks panel

#### Scenario: Scout single company triggered
- **WHEN** the user selects a specific company from the scout dropdown and clicks Run
- **THEN** `POST /api/scout/{company_name}` is called with the selected company name

#### Scenario: Enrich with limit triggered
- **WHEN** the user selects "10" from the enrich limit dropdown and clicks Run
- **THEN** `POST /api/enrich/next` is called with body `{"limit": 10}`

#### Scenario: Enrich all triggered
- **WHEN** "All" is selected from the enrich limit dropdown and Run is clicked
- **THEN** `POST /api/enrich/all` is called

#### Scenario: Evaluate with limit triggered
- **WHEN** the user selects "50" from the evaluate limit dropdown and clicks Run
- **THEN** `POST /api/evaluate/next` is called with body `{"limit": 50}`

#### Scenario: Evaluate all triggered
- **WHEN** "All" is selected from the evaluate limit dropdown and Run is clicked
- **THEN** `POST /api/evaluate/all` is called

#### Scenario: Pending badge hidden when queue is empty
- **WHEN** a stage has zero jobs queued
- **THEN** the pending count badge for that stage is not displayed

#### Scenario: Pending badge shown when jobs are queued
- **WHEN** one or more jobs are in a stage's input state (e.g. discovered jobs pending enrich)
- **THEN** the badge displays the count next to the stage title

### Requirement: Running Tasks panel shows live operation status
The frontend SHALL display a Running Tasks panel listing active and recently
completed operations. Each entry SHALL show the operation name, status
(running / done / failed), elapsed or completion time, and — when the task
is done or failed — per-item log events (scout: per-company results;
enrich: summary count; evaluate: per-job score and routing decision).
Completed tasks SHALL auto-dismiss after 120 seconds. A "Delete" button
SHALL appear in a dedicated actions row at the bottom of each completed
or failed task entry; clicking it SHALL immediately remove the entry.
No dismiss control SHALL appear on running tasks.

#### Scenario: Running task appears after triggering operation
- **WHEN** the user triggers any pipeline operation
- **THEN** within 5 seconds a new entry appears in the Running Tasks panel with status "running"

#### Scenario: Task transitions to done with results
- **WHEN** a running task completes
- **THEN** the panel entry updates to show status "done", the per-item log events are displayed below, and the job list is automatically refreshed

#### Scenario: Failed task shown with error
- **WHEN** a pipeline operation fails
- **THEN** the task entry is shown with status "failed" and an error indicator

#### Scenario: Completed task auto-dismissed
- **WHEN** a task has been in done or failed state for 120 seconds
- **THEN** the task entry is removed from the panel automatically

#### Scenario: User deletes completed task
- **WHEN** the user clicks "Delete" on a completed or failed task entry
- **THEN** the entry is immediately removed from the panel

#### Scenario: Delete button absent on running tasks
- **WHEN** a task is in running state
- **THEN** no Delete button is shown for that task entry

### Requirement: Job list with search and status filter
The frontend SHALL display the job list with a search input (filters by title and company) and status filter pills (All, Discovered, Parsed, Match, Review, Archived, Applied). Filtering SHALL be client-side with no additional API calls.

#### Scenario: Search filters job list
- **WHEN** the user types in the search input
- **THEN** only jobs whose title or company contains the search string are shown

#### Scenario: Status pill filters job list
- **WHEN** the user clicks a status pill
- **THEN** only jobs with that state are shown

#### Scenario: All pill resets filter
- **WHEN** the user clicks the "All" status pill
- **THEN** all jobs are shown regardless of state

### Requirement: Per-job state-aware action buttons on card view
Each job card SHALL display action buttons appropriate to the job's current state. For `discovered` state: Enrich and Run All buttons. For `parsed` state: Evaluate and Run All buttons. For all other states: no action buttons.

#### Scenario: Discovered job shows enrich and run all
- **WHEN** a job card with state `discovered` is rendered
- **THEN** an Enrich button and a Run All button are visible on the card

#### Scenario: Parsed job shows evaluate and run all
- **WHEN** a job card with state `parsed` is rendered
- **THEN** an Evaluate button and a Run All button are visible on the card

#### Scenario: Enrich button fires single-job enrich
- **WHEN** the user clicks Enrich on a job card
- **THEN** `POST /api/enrich/{job_id}` is called and the task appears in Running Tasks

#### Scenario: Run All button fires run-all endpoint
- **WHEN** the user clicks Run All on a job card
- **THEN** `POST /api/jobs/{job_id}/run` is called and the task appears in Running Tasks

### Requirement: Expanded job detail panel with action buttons
Clicking a job card SHALL expand an inline detail panel showing all available job fields (title, company, location, score, matched skills, summary, links). The detail panel SHALL also display the same state-aware action buttons as the card view.

#### Scenario: Card expands on click
- **WHEN** the user clicks a job card
- **THEN** the detail panel expands inline showing enriched job data

#### Scenario: Card collapses on second click
- **WHEN** the user clicks an already-expanded job card
- **THEN** the detail panel collapses

#### Scenario: Detail panel shows action buttons
- **WHEN** a job card is expanded and the job is in `discovered` or `parsed` state
- **THEN** the same Enrich/Evaluate and Run All buttons are visible in the detail panel

### Requirement: Job list refreshes after task completion
The frontend SHALL automatically re-fetch `GET /api/jobs` whenever a task transitions from `running` to `done`, updating the displayed job states and counts without a full page reload.

#### Scenario: Job state updates after enrich completes
- **WHEN** an enrich task completes
- **THEN** the job list refreshes and the enriched job's state badge updates from `discovered` to `parsed`

### Requirement: Dark mode toggle
The frontend SHALL support dark and light themes toggleable by the user, persisted in `localStorage`.

#### Scenario: Dark mode persists across reload
- **WHEN** the user enables dark mode and reloads the page
- **THEN** the page loads in dark mode

### Requirement: Fit reasons visible on list card
The job list card SHALL render the `reasons` array as a plain bulleted list below the score-tag row whenever the job has been evaluated and `reasons` is non-empty. The list SHALL use the same font size as the detail drawer's Fit Reasons section (`0.85rem`). The section SHALL be hidden (via `x-show`) when `reasons` is absent or empty, producing no layout shift for unevaluated jobs.

#### Scenario: Evaluated job shows fit reasons on card
- **WHEN** a job card is rendered and the job has a non-empty `reasons` array
- **THEN** the reasons are displayed as a bulleted list below the score tags, without requiring the card to be expanded

#### Scenario: Unevaluated job shows no reasons section
- **WHEN** a job card is rendered and the job has no `reasons` array or an empty array
- **THEN** no reasons section is visible and the card height is unchanged

#### Scenario: Reasons match detail drawer content
- **WHEN** the user compares the fit reasons on the card to those in the expanded detail drawer
- **THEN** the same bullet points appear in both places
