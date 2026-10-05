# Spec Delta

## ADDED Requirements

### Requirement: Settings view surfaces persistence problems
The settings view SHALL tell the user when settings cannot be persisted and why. When `PUT /api/settings` fails, the error shown SHALL include the server-provided `error` message when the response contains one, falling back to the HTTP status otherwise. When `GET /api/settings` reports `meta.writable: false`, the settings view SHALL show a persistent warning banner above the sections stating that changes cannot be saved, showing `meta.path`, and pointing to `RADAR_SETTINGS_PATH` as the fix. Save buttons SHALL remain enabled so a fixed deployment works without a reload.

#### Scenario: Save failure shows the server's reason
- **WHEN** the user clicks a settings Save button and `PUT /api/settings` returns 500 with `{"ok": false, "error": "Cannot write /app/configs/settings.yaml: [Errno 30] Read-only file system"}`
- **THEN** the UI error message contains "Read-only file system" and the path, and no "Saved" confirmation is shown

#### Scenario: Save failure without a JSON body falls back to status
- **WHEN** `PUT /api/settings` returns a non-2xx response whose body is not JSON (e.g. a reverse-proxy error page)
- **THEN** the UI error message includes the HTTP status code

#### Scenario: Read-only banner shown on load
- **WHEN** the settings view is opened and `GET /api/settings` returned `meta: {"path": "/app/configs/settings.yaml", "writable": false}`
- **THEN** a warning banner is visible stating settings cannot be saved, showing `/app/configs/settings.yaml`, and mentioning `RADAR_SETTINGS_PATH`

#### Scenario: No banner when writable
- **WHEN** `GET /api/settings` returned `meta.writable: true`
- **THEN** no read-only banner is shown
