# Specification: App Settings Capability

## Purpose

TBD — manages persistent pipeline configuration overrides stored in `configs/settings.yaml`, covering scout, enrich, and evaluate stages with per-stage model selection and fallback to environment variables.

## Requirements

### Requirement: Settings file stores pipeline configuration overrides
The system SHALL read pipeline configuration from `configs/settings.yaml`. The file is optional — if absent or a key is missing, the system SHALL fall back to the hardcoded dataclass default for that field. The file is always written in full on save (no sparse partial writes).

#### Scenario: Missing file uses all defaults
- **WHEN** `configs/settings.yaml` does not exist
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
- **THEN** the file content is identical to what was received (all defaults preserved)

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
