## Purpose

Dashboard UI for the job favorites feature. Each job card exposes a star button to toggle favorite state, and a filter toggle limits the job list to favorited jobs only.

## Requirements

### Requirement: Star button appears on every job card
The dashboard SHALL display a star button on each job card that reflects and toggles the job's `favorited` state.

#### Scenario: Unfavorited job shows empty star
- **WHEN** a job card is rendered and `job.favorited` is absent or `false`
- **THEN** the star button SHALL appear in an unfilled/inactive style (☆)

#### Scenario: Favorited job shows filled star
- **WHEN** a job card is rendered and `job.favorited` is `true`
- **THEN** the star button SHALL appear in a filled/active style (★)

#### Scenario: Clicking star toggles favorite
- **WHEN** the user clicks the star button on a job card
- **THEN** the frontend SHALL call `PATCH /jobs/{job_id}/favorite` and update `job.favorited` to the returned value without a full page reload

### Requirement: Dashboard has a favorites-only filter toggle
The dashboard SHALL provide a toggle that, when active, limits the job list to favorited jobs only.

#### Scenario: Favorites filter off — all jobs shown
- **WHEN** the favorites filter is inactive
- **THEN** `filteredJobs` SHALL apply no favorites constraint (existing status and search filters apply normally)

#### Scenario: Favorites filter on — only favorited jobs shown
- **WHEN** the favorites filter is active
- **THEN** `filteredJobs` SHALL include only jobs where `favorited` is `true`, combined with any active status and search filters

#### Scenario: Favorites filter interacts correctly with status filter
- **WHEN** both a status filter and the favorites filter are active
- **THEN** only jobs matching both constraints SHALL be shown
