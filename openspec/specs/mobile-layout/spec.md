# Spec: Mobile Layout

## Purpose

Defines how the web UI adapts to narrow (mobile) viewports. Covers sidebar reflow, default collapsed state on mobile, the toggle button behaviour, and the wrapping/scrolling of filter controls and action buttons.

---

## Requirements

### Requirement: Sidebar reflows above content on mobile viewports
On viewports narrower than 768px, the sidebar SHALL be repositioned from a fixed left column to a panel that appears above the main content. The main content SHALL span the full viewport width with no left margin offset.

#### Scenario: Phone-width viewport — sidebar above content
- **WHEN** the page is viewed on a viewport narrower than 768px
- **THEN** the sidebar is positioned above the main content area, not beside it

#### Scenario: Phone-width viewport — content fills width
- **WHEN** the page is viewed on a viewport narrower than 768px
- **THEN** the main content area fills the full viewport width with no left margin

#### Scenario: Desktop viewport — layout unchanged
- **WHEN** the page is viewed on a viewport 768px wide or wider
- **THEN** the sidebar remains in its fixed left-panel position and the content retains its left margin offset

### Requirement: Sidebar is collapsed by default on mobile
On mobile viewports the sidebar SHALL be hidden by default when the page loads, so the job list is immediately visible without requiring the user to dismiss the filter panel first.

#### Scenario: Initial page load on mobile
- **WHEN** a user opens the page on a viewport narrower than 768px
- **THEN** the sidebar is collapsed and the main content is fully visible

#### Scenario: Initial page load on desktop
- **WHEN** a user opens the page on a viewport 768px wide or wider
- **THEN** the sidebar is expanded by default (existing behaviour preserved)

### Requirement: Mobile sidebar toggle shows and hides the filter panel
The existing hamburger toggle in the top navigation bar SHALL expand and collapse the sidebar as a vertically-stacked panel above the content on mobile viewports.

#### Scenario: Toggle opens mobile sidebar
- **WHEN** the user taps the toggle button while the mobile sidebar is collapsed
- **THEN** the sidebar panel appears above the main content and is scrollable if taller than the viewport

#### Scenario: Toggle closes mobile sidebar
- **WHEN** the user taps the toggle button while the mobile sidebar is expanded on mobile
- **THEN** the sidebar panel is hidden and the main content returns to full visible height

### Requirement: Filter controls and action bar adapt to narrow viewports
The sort bar, filter chips, and action buttons SHALL wrap or scroll horizontally rather than overflow off-screen on viewports narrower than 768px. Touch targets SHALL be at least 44px in height.

#### Scenario: Sort bar wraps on mobile
- **WHEN** the sort bar is rendered on a viewport narrower than 768px
- **THEN** its elements wrap to multiple lines rather than extending beyond the viewport edge

#### Scenario: Action buttons remain reachable on mobile
- **WHEN** any action button (Scout, Evaluate, etc.) is rendered on a viewport narrower than 768px
- **THEN** the button is fully visible and tappable within the viewport bounds
