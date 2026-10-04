# Spec Delta

## MODIFIED Requirements

### Requirement: Settings file stores pipeline configuration overrides
The system SHALL read pipeline configuration from the settings file, which is `configs/settings.yaml` unless overridden by `RADAR_SETTINGS_PATH` (see "Settings file location is configurable"). The file is optional — if absent or a key is missing, the system SHALL fall back to the hardcoded dataclass default for that field. On save, the editable sections (`scout`, `enrich`, `evaluate`, `archival`) are written in full; other top-level sections (e.g. `notifications`) SHALL be preserved from the existing file.

#### Scenario: Missing file uses all defaults
- **WHEN** `configs/settings.yaml` does not exist and `RADAR_SETTINGS_PATH` is unset
- **THEN** all pipeline operations run with default values (respect_robots=true, max_pages=10, concurrency=5, etc.)

#### Scenario: Partial file merges with defaults
- **WHEN** `configs/settings.yaml` exists with only `scout.respect_robots: false`
- **THEN** scout runs with `respect_robots=false` and all other settings at their defaults

## ADDED Requirements

### Requirement: Settings file location is configurable
The system SHALL resolve the settings file path from the `RADAR_SETTINGS_PATH` environment variable when it is set and non-empty; otherwise it SHALL use `configs/settings.yaml` under the project root. A relative `RADAR_SETTINGS_PATH` SHALL be resolved against the project root. All settings reads (pipeline config, notifications, the settings API) and all settings writes SHALL use the resolved path, so a deployment can mount `configs/` read-only and persist settings on a writable volume.

#### Scenario: Default path when env var unset
- **WHEN** `RADAR_SETTINGS_PATH` is unset
- **THEN** settings are read from and written to `configs/settings.yaml`

#### Scenario: Override path used for reads and writes
- **WHEN** `RADAR_SETTINGS_PATH=/app/artifacts/settings.yaml` and that file contains `scout.max_pages: 15`
- **THEN** the scout pipeline runs with `max_pages=15`, and a subsequent settings save writes to `/app/artifacts/settings.yaml` without touching `configs/settings.yaml`

#### Scenario: Missing override file falls back to bundled settings
- **WHEN** `RADAR_SETTINGS_PATH` points to a file that does not exist and `configs/settings.yaml` exists with `evaluate.auto_match_threshold: 7.5` and a `notifications.telegram` block
- **THEN** settings are read from `configs/settings.yaml` (so `auto_match_threshold=7.5`), and the first save creates the override file (including any missing parent directories) containing the edited sections plus the preserved `notifications.telegram` block
