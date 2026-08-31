# frontend-stats-integration Specification

## Purpose
TBD - created by archiving change frontend-query-optimization. Update Purpose after archive.
## Requirements
### Requirement: Direct Dashboard Stats Fetching
The frontend application SHALL fetch state counts from `GET /api/jobs/stats` during initialization and task updates instead of running multi-pass client-side filter loops.

#### Scenario: Stats initialization and refresh
- **WHEN** the dashboard loads or background pipeline tasks complete
- **THEN** state statistics SHALL be updated by requesting `/api/jobs/stats`.

### Requirement: Debounced Search Input
The frontend search filter input SHALL debounce keystrokes by 300ms before triggering filtering updates.

#### Scenario: User typing search query
- **WHEN** the user types characters into the search bar
- **THEN** search evaluation SHALL be delayed until 300ms after the last keystroke, preventing UI thread freezing.

