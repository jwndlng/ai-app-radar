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
The frontend SHALL display a persistent top action bar with controls for scout, enrich, and evaluate operations. Scout SHALL have an optional text input (empty = all companies, filled = single company). Enrich and evaluate SHALL each have a dropdown with options: All, 5, 10, 50.

#### Scenario: Scout all triggered
- **WHEN** the scout input is empty and the Scout button is clicked
- **THEN** `POST /api/scout` is called and the new task appears in the Running Tasks panel

#### Scenario: Scout single company triggered
- **WHEN** the user types a company name in the scout input and clicks Scout
- **THEN** `POST /api/scout/{company_name}` is called with the entered name

#### Scenario: Enrich with limit triggered
- **WHEN** the user selects "10" from the enrich dropdown and clicks Enrich
- **THEN** `POST /api/enrich/next` is called with body `{"limit": 10}`

#### Scenario: Enrich all triggered
- **WHEN** "All" is selected from the enrich dropdown and Enrich is clicked
- **THEN** `POST /api/enrich/all` is called

#### Scenario: Evaluate with limit triggered
- **WHEN** the user selects "50" from the evaluate dropdown and clicks Evaluate
- **THEN** `POST /api/evaluate/next` is called with body `{"limit": 50}`

#### Scenario: Evaluate all triggered
- **WHEN** "All" is selected from the evaluate dropdown and Evaluate is clicked
- **THEN** `POST /api/evaluate/all` is called

### Requirement: Running Tasks panel shows live operation status
The frontend SHALL display a Running Tasks panel listing active and recently completed operations. Each entry SHALL show the operation name, status (running / done / failed), and elapsed or completion time. The panel SHALL poll `GET /api/tasks` every 2 seconds.

#### Scenario: Running task appears after triggering operation
- **WHEN** the user triggers any pipeline operation
- **THEN** within 2 seconds a new entry appears in the Running Tasks panel with status "running"

#### Scenario: Task transitions to done
- **WHEN** a running task completes
- **THEN** the panel entry updates to show status "done" and the job list is automatically refreshed

#### Scenario: Failed task shown in red
- **WHEN** a pipeline operation fails
- **THEN** the task entry is shown with status "failed" and an error indicator

#### Scenario: Empty tasks panel
- **WHEN** no tasks have been run yet
- **THEN** the Running Tasks panel shows a placeholder message

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
