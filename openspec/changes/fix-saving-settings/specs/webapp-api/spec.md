# Spec Delta

## MODIFIED Requirements

### Requirement: Settings read endpoint
The system SHALL expose `GET /api/settings` returning the full current settings as a JSON object with all fields populated (defaults filled in for any absent file keys). The response SHALL additionally include a `meta` object `{"path": "<resolved settings file path>", "writable": <bool>}`, where `writable` reports whether a save to that path is expected to succeed (the file is writable, or it does not exist and its nearest existing parent directory is writable). `PUT /api/settings` SHALL ignore a `meta` key in its body.

#### Scenario: Settings returned with defaults when file absent
- **WHEN** `GET /api/settings` is called and `configs/settings.yaml` does not exist
- **THEN** the response has status 200 and body contains all settings fields at their default values

#### Scenario: Settings returned with overrides from file
- **WHEN** `GET /api/settings` is called and `configs/settings.yaml` has `scout.respect_robots: false`
- **THEN** the response body contains `{"scout": {"respect_robots": false, ...other defaults...}, ...}`

#### Scenario: Read-only settings reported
- **WHEN** `GET /api/settings` is called and the resolved settings file is on a read-only filesystem or not writable by the server process
- **THEN** the response has status 200 and contains `"meta": {"path": "<resolved path>", "writable": false}`

#### Scenario: Writable settings reported
- **WHEN** `GET /api/settings` is called and the resolved settings file is writable
- **THEN** the response contains `"meta": {"path": "<resolved path>", "writable": true}`

### Requirement: Settings write endpoint
The system SHALL expose `PUT /api/settings` accepting a full settings JSON object and writing the editable sections (`scout`, `enrich`, `evaluate`, `archival`) to the resolved settings file (`configs/settings.yaml` unless `RADAR_SETTINGS_PATH` is set). Sections not managed by the settings UI (notably `notifications`) SHALL be preserved from the existing file rather than overwritten. On success it SHALL return `{"ok": true}`. When the file cannot be written, it SHALL return status 500 with `{"ok": false, "error": "<message>", "path": "<resolved path>"}`, where the message names the path and the underlying OS error, and SHALL log the failure server-side.

#### Scenario: Settings saved successfully
- **WHEN** `PUT /api/settings` is called with a valid settings body
- **THEN** the resolved settings file is written with the provided values and the response is `{"ok": true}` with status 200

#### Scenario: Save preserves the notifications section
- **WHEN** the settings file contains a `notifications.telegram` block and `PUT /api/settings` is called
- **THEN** the saved file SHALL still contain the original `notifications.telegram` block unchanged

#### Scenario: Subsequent GET reflects saved values
- **WHEN** `PUT /api/settings` is called with `{"scout": {"max_pages": 15}, ...}` followed by `GET /api/settings`
- **THEN** the GET response contains `scout.max_pages: 15`

#### Scenario: Write failure returns a descriptive error
- **WHEN** `PUT /api/settings` is called and writing the settings file fails (e.g. read-only filesystem or permission denied)
- **THEN** the response has status 500 with `ok: false`, an `error` message containing the resolved path and the OS error text (e.g. "Read-only file system"), and the `path` field set to the resolved path; the failure is logged
