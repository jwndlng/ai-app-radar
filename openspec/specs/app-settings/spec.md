# Specification: App Settings Capability

## Purpose

TBD — manages persistent pipeline configuration overrides stored in `configs/settings.yaml`, covering scout, enrich, and evaluate stages with per-stage model selection and fallback to environment variables.

## Requirements

### Requirement: Settings file stores pipeline configuration overrides
The system SHALL read pipeline configuration from the settings file, which is `configs/settings.yaml` unless overridden by `RADAR_SETTINGS_PATH` (see "Settings file location is configurable"). The file is optional — if absent or a key is missing, the system SHALL fall back to the hardcoded dataclass default for that field. On save, the editable sections (`scout`, `enrich`, `evaluate`, `archival`) are written in full; other top-level sections (e.g. `notifications`) SHALL be preserved from the existing file.

#### Scenario: Missing file uses all defaults
- **WHEN** `configs/settings.yaml` does not exist and `RADAR_SETTINGS_PATH` is unset
- **THEN** all pipeline operations run with default values (respect_robots=true, max_pages=10, concurrency=5, etc.)

#### Scenario: Partial file merges with defaults
- **WHEN** `configs/settings.yaml` exists with only `scout.respect_robots: false`
- **THEN** scout runs with `respect_robots=false` and all other settings at their defaults

### Requirement: Settings file schema covers scout, enrich, and evaluate sections
The system SHALL support the following structure in `configs/settings.yaml`:

```yaml
scout:
  respect_robots: true      # bool, default true
  max_pages: 10             # int, default 10
  worker_count: 10          # int, default 10
  model: null               # string|null, default null (falls back to SCOUT_MODEL env var)

enrich:
  concurrency: 5            # int, default 5
  checkpoint_every: 5       # int, default 5
  model: null               # string|null, default null

evaluate:
  auto_reject_threshold: 4.0   # float, default 4.0
  auto_match_threshold: 8.5    # float, default 8.5
  location_reject_threshold: 2.0  # float, default 2.0
  scoring_weights:
    fit: 0.5                   # float, default 0.5
    location: 0.2              # float, default 0.2
    seniority: 0.2             # float, default 0.2
    compensation: 0.1          # float, default 0.1
  model: null                  # string|null, default null
```

#### Scenario: Full settings file round-trips correctly
- **WHEN** `GET /api/settings` is called, then the result is POSTed back via `PUT /api/settings`
- **THEN** the editable sections round-trip unchanged and any existing `notifications` block in the file is preserved (the GET payload's flat notifications object is never written back over it)

### Requirement: Model setting per pipeline stage falls back to environment variable
When a stage's `model` key is `null` or absent in `settings.yaml`, the system SHALL fall back to the corresponding environment variable (`SCOUT_MODEL`, `ENRICH_MODEL`, `EVALUATE_MODEL`). When set to a non-null string, the settings file value SHALL take precedence over the env var.

#### Scenario: Null model uses env var
- **WHEN** `settings.yaml` has `scout.model: null` and `SCOUT_MODEL=gemini-2.5-flash` is set
- **THEN** the scout pipeline uses `gemini-2.5-flash`

#### Scenario: Settings model overrides env var
- **WHEN** `settings.yaml` has `scout.model: claude-sonnet-4-6` and `SCOUT_MODEL=gemini-2.5-flash` is set
- **THEN** the scout pipeline uses `claude-sonnet-4-6`

### Requirement: Robots.txt respected when setting is enabled
When `scout.respect_robots` is `true`, the system SHALL check `robots.txt` for each domain before fetching any page via the `agent_review` provider. If the page is disallowed for `User-agent: *`, the provider SHALL skip that company and log a warning.

#### Scenario: Robots disallows — company skipped
- **WHEN** `respect_robots=true` and a company's domain `robots.txt` disallows `*` for the careers URL
- **THEN** the scout provider skips fetching that company's page and logs `[robots] <company>: blocked`

#### Scenario: Robots allows — company fetched normally
- **WHEN** `respect_robots=true` and a company's domain `robots.txt` allows `*` for the careers URL
- **THEN** the scout provider fetches the page as normal

#### Scenario: Robots disabled — all companies fetched
- **WHEN** `respect_robots=false`
- **THEN** no robots.txt check is performed and all companies are fetched regardless

### Requirement: Settings file schema includes a notifications section
The system SHALL support an optional `notifications` top-level key in `configs/settings.yaml` alongside the existing `scout`, `enrich`, and `evaluate` sections. When absent, all notification settings SHALL default to disabled (no notifications sent). The `AppSettings` dataclass SHALL include a `NotificationSettings` field, and `AppConfigLoader` SHALL expose a `notifications()` method returning a `NotificationSettings` dataclass.

#### Scenario: Missing notifications block defaults to no-op
- **WHEN** `configs/settings.yaml` has no `notifications` key
- **THEN** `AppConfigLoader.notifications()` returns a `NotificationSettings` with `bot_token=None` and `chat_id=None`

#### Scenario: Notifications block is parsed correctly
- **WHEN** `configs/settings.yaml` contains a valid `notifications.telegram` block with `bot_token` and `chat_id` set
- **THEN** `AppConfigLoader.notifications()` returns those values in the `NotificationSettings` dataclass

### Requirement: Telegram credentials fall back to environment variables
When `notifications.telegram.bot_token` or `chat_id` is `null` or absent in `settings.yaml`, the system SHALL fall back to `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` environment variables respectively, consistent with the existing `SCOUT_MODEL` / `ENRICH_MODEL` / `EVALUATE_MODEL` pattern.

#### Scenario: Null token uses env var
- **WHEN** `settings.yaml` has `notifications.telegram.bot_token: null` and `TELEGRAM_BOT_TOKEN=abc123` is set
- **THEN** `AppConfigLoader.notifications()` returns `bot_token="abc123"`

#### Scenario: Settings value overrides env var
- **WHEN** `settings.yaml` has `notifications.telegram.bot_token: "from-file"` and `TELEGRAM_BOT_TOKEN=from-env` is set
- **THEN** `AppConfigLoader.notifications()` returns `bot_token="from-file"`

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
