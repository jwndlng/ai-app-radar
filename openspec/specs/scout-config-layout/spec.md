# Specification: Scout Config Layout

## Purpose
Scout configuration is split across a single flat company registry and profile-based filters, eliminating the monolithic `scout.yaml` and per-category YAML files.

## Requirements

### Requirement: load_scout_config assembles config from split files
The system SHALL provide a `load_scout_config(root_dir)` function that reads `profile.yaml` (filters) and `configs/companies.json` (companies), and returns a dict with keys `title_filter` and `tracked_companies` matching the shape required by `scout_orchestrator`.

#### Scenario: Assembled config is compatible with scout_orchestrator
- **WHEN** `load_scout_config` is called
- **THEN** the returned dict SHALL contain `title_filter` (from `profile.yaml`) and `tracked_companies` (from `configs/companies.json`) so that `scout_orchestrator` requires no changes

#### Scenario: Only enabled companies included
- **WHEN** `configs/companies.json` contains entries with `enabled: false`
- **THEN** `load_scout_config` SHALL exclude those entries from `tracked_companies`

### Requirement: RSS feed scanning removed
The system SHALL NOT contain an RSS feed scanning loop or `RSSProvider`. `feedparser` SHALL be removed from dependencies.

#### Scenario: SwissDevJobs via agent_review
- **WHEN** the scout runs
- **THEN** SwissDevJobs SHALL be scanned as a regular `agent_review` company entry, not via RSS

### Requirement: scout.yaml removed
The file `configs/scout.yaml` SHALL be deleted. Any direct reference to it in `src/flows/scout/main.py`, `src/flows/scout/scout.py`, and `src/main.py` SHALL be replaced with calls to `load_scout_config`.

#### Scenario: Scout runs without scout.yaml present
- **WHEN** `configs/scout.yaml` does not exist
- **THEN** the scout SHALL load config successfully from the new layout
