# Specification: UI Capability

## Purpose
To provide a high-fidelity, interactive, and secure dashboard for reviewing job discovery results and performing strategic triage.

## Requirements

### Requirement: CSS Grid Alignment
The UI SHALL use a fixed-column CSS grid for the summary row to ensure Title, Company, Status, and Score align perfectly across all rows.

#### Scenario: Viewing the job list
- **WHEN** the user views the dashboard
- **THEN** the job rows display in a vertically aligned data-grid structure

### Requirement: Classic Typography and Color Aesthetics
The UI SHALL employ a colorful design palette, moving away from stark minimalism, and utilize a classical serif font (e.g., Georgia or Garamond) for primary elements to present a distinguished and elegant structure.

#### Scenario: Assessing visual feel
- **WHEN** the user opens the dashboard
- **THEN** they see an interface titled "Agentic Application Dashboard" accented with warm colors and a classic, non-modern font setup

### Requirement: Summary Grid Columns
The summary grid SHALL display the following columns in order:
1. Expansion Toggle
2. Job Title
3. Company
4. Location
5. Status
6. Score

### Requirement: Explicit Filter Labels
All filter inputs in the control bar SHALL have explicit, linked labels for improved accessibility and clarity.

### Requirement: Default Relevance Shield
The dashboard SHALL filter out all roles with the status "Not relevant" by default upon initial load.

#### Scenario: Initial Load
- **WHEN** the dashboard is loaded
- **THEN** only "relevant" roles are displayed, and the status filter indicates the exclusion of "Not relevant" items.

### Requirement: Header-Based Sorting
The UI SHALL provide clickable table headers in the grid for sorting, replacing the previous standalone sort buttons.

#### Scenario: Sorting by Score
- **WHEN** the user clicks the "Score" column header
- **THEN** the list sorts by score and the header visually indicates the active sort state

### Requirement: Row State Management
The system SHALL maintain consistent grid layout and column alignment even when a row is expanded or collapsed.

#### Scenario: Expanding a row
- **WHEN** the user expands a job row to view details
- **THEN** the summary grid columns remain perfectly aligned with the table headers and other rows

### Requirement: Glassmorphic Aesthetic
The UI SHALL use a modern, glassmorphic design system (blur, transparency, high-contrast tokens) to ensure a premium discovery experience.

### Requirement: HTML Sanitization
To ensure security and stability, the system SHALL strip all HTML tags (specifically scripts and styles) from external Job Description content before rendering. This prevents "frame-busting" redirects and XSS risks.

### Requirement: Multi-dimensional Filtering
The dashboard SHALL provide an interactive filter grid enabling simultaneous triage across:
- **Score**: Sequential thresholding (0-10)
- **Status**: Pipeline state filtering (Applied, Hot, etc.)
- **Search**: Fuzzy matching across Company and Title
- **Location**: Sub-string matching for geographic triage

#### Scenario: Filtering by Score and Location
- **WHEN** the user inputs a minimum score and a location text
- **THEN** the dashboard immediately filters to show only rows matching both conditions

### Requirement: Fixed top navigation bar
The UI SHALL render a fixed top navigation bar that remains visible as the user scrolls, providing persistent access to global navigation controls.

### Requirement: Multi-view routing via Alpine currentView
The UI SHALL use an Alpine.js `currentView` data property to manage client-side routing between views, switching content without a full page reload.

### Requirement: Sidebar hidden on companies view
The UI SHALL hide the sidebar when the active view is the companies view, giving the companies layout full horizontal space.

### Requirement: Companies view with search and toggle
The UI SHALL include a dedicated companies view that lists all configured companies with a search input for filtering by name and a toggle control to enable or disable each company.

### Requirement: Optimistic toggle with rollback
When the user toggles a company's enabled state, the UI SHALL update the toggle immediately (optimistic update) and roll back to the previous state if the server request fails.

### Requirement: Gear icon opens settings view
The UI SHALL render a ⚙ gear icon button in the top-right of the fixed navigation bar. Clicking it SHALL set `currentView = 'settings'` and clicking it again (or any nav tab) SHALL return to the previous view.

#### Scenario: Gear icon navigates to settings
- **WHEN** the user clicks the ⚙ gear icon
- **THEN** `currentView` is set to `'settings'` and the settings view is shown

#### Scenario: Nav tab exits settings
- **WHEN** the user is in settings view and clicks the Jobs tab
- **THEN** `currentView` is set to `'jobs'` and the settings view is hidden

### Requirement: Settings view with per-section save
The UI SHALL render a settings view with three sections — Scout, Enrich, and Evaluate. Each section SHALL have its own Save button. All Save buttons SHALL call the same handler which sends `PUT /api/settings` with the full current settings object and shows a brief success confirmation.

#### Scenario: Save button writes full settings
- **WHEN** the user edits `max_pages` in the Scout section and clicks the Scout Save button
- **THEN** `PUT /api/settings` is called with the complete settings object (all three sections)

#### Scenario: Success feedback shown after save
- **WHEN** `PUT /api/settings` returns `{"ok": true}`
- **THEN** the Save button briefly shows a "Saved" confirmation state before returning to normal

### Requirement: Sidebar hidden in settings view
The UI SHALL hide the sidebar when `currentView === 'settings'`, giving the settings layout full horizontal space.

#### Scenario: Sidebar absent in settings view
- **WHEN** the user is in settings view
- **THEN** the sidebar is not visible and the settings content fills the full main area width

### Requirement: Settings form fields match settings schema
The settings view SHALL render appropriately typed form controls for each setting:
- Boolean fields (`respect_robots`) as toggle switches
- Integer fields (`max_pages`, `worker_count`, `concurrency`, `checkpoint_every`) as number inputs
- Float fields (`auto_reject_threshold`, `auto_match_threshold`, scoring weights) as number inputs with step 0.05
- Model fields as dropdowns listing known model IDs plus a null/"default" option
- Scoring weights section SHALL show a live sum indicator

#### Scenario: Scoring weights sum displayed
- **WHEN** the user edits any scoring weight value
- **THEN** the live sum of all four weights is displayed next to the section heading

### Requirement: Job Source Links
The dashboard job detail panel SHALL display source links with clear visual hierarchy:
a single canonical "Listing" button links to `job.url`. When a job has been
re-discovered more than once, a quiet "re-posted N×" note is shown alongside it.

#### Scenario: Single source
- **WHEN** a job has exactly one source
- **THEN** a single "Listing" button is shown linking to job.url with no re-posted note

#### Scenario: Multiple sources
- **WHEN** a job has two or more sources
- **THEN** a "Listing" button is shown alongside a "re-posted N×" label

#### Scenario: No sources array
- **WHEN** a job has no sources array
- **THEN** a fallback "Listing" link using job.url is shown
