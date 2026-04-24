# Specification: Scout Config Layout

## Purpose
Scout configuration is split across a single flat company registry and profile-based filters, eliminating the monolithic `scout.yaml` and per-category YAML files.

## Requirements

### Requirement: AppConfigLoader.scout() assembles config from split files
The system SHALL provide `AppConfigLoader.scout()` in `src/core/config.py` that reads `profile.yaml` (filters under `scout_filters:`) and `configs/companies.json` (companies), and returns the configuration required by `ScoutTask` / `PipelineRuntime`.

#### Scenario: Assembled config is compatible with ScoutTask
- **WHEN** `AppConfigLoader.scout()` is called
- **THEN** it SHALL return title filters (from `profile.yaml` `scout_filters:`) and tracked companies (from `configs/companies.json`) consumed by `ScoutTask` and `PipelineRuntime`

#### Scenario: Only enabled companies included
- **WHEN** `configs/companies.json` contains entries with `enabled: false`
- **THEN** `load_scout_config` SHALL exclude those entries from `tracked_companies`

### Requirement: RSS feed scanning removed
The system SHALL NOT contain an RSS feed scanning loop or `RSSProvider`. `feedparser` SHALL be removed from dependencies.

#### Scenario: SwissDevJobs via agent_review
- **WHEN** the scout runs
- **THEN** SwissDevJobs SHALL be scanned as a regular `agent_review` company entry, not via RSS

### Requirement: scout.yaml removed
The file `configs/scout.yaml` SHALL be deleted. Any direct reference to it in `src/scout/` and `src/cli.py` SHALL be replaced with calls to `AppConfigLoader.scout()`.

#### Scenario: Scout runs without scout.yaml present
- **WHEN** `configs/scout.yaml` does not exist
- **THEN** the scout SHALL load config successfully from the new layout
