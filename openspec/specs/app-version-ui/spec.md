# app-version-ui

## Purpose

Displays the running app version as a subtitle beneath the main app title, fetched from the `/api/version` endpoint on page load.

## Requirements

### Requirement: App version displayed below the title
The frontend SHALL display the app version as a subtitle directly beneath the
"AI-powered Application Radar" title. The value SHALL be fetched from `GET /api/version`
on page load and rendered as the `version` field from the response.

#### Scenario: Version shown after load
- **WHEN** the page finishes loading and the `/api/version` response is received
- **THEN** the version string (e.g. `v0.2.1`) is visible below the app title

#### Scenario: Version hidden until fetched
- **WHEN** the page has loaded but the `/api/version` response has not yet arrived
- **THEN** no version text or placeholder is shown (element is hidden)

#### Scenario: Local dev version
- **WHEN** the app is running locally without `APP_VERSION` set
- **THEN** the subtitle displays `dev`
