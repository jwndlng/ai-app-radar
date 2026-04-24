# Specification: Profile Scout Filters

## Purpose
Job title filters live in `profile.yaml` under `scout_filters`, making them user-specific and eliminating the separate `scout.yaml` filter section.

## Requirements

### Requirement: profile.yaml contains scout_filters section
`configs/profile.yaml` SHALL include a `scout_filters:` top-level section with `positive`, `negative`, and `seniority_boost` lists, replacing the `title_filter:` section previously in `scout.yaml`.

#### Scenario: Filters loaded from profile
- **WHEN** `load_scout_config` is called
- **THEN** `title_filter` in the returned config SHALL be populated from `profile.yaml`'s `scout_filters:` section

#### Scenario: Missing scout_filters falls back to empty
- **WHEN** `profile.yaml` has no `scout_filters:` section
- **THEN** the loader SHALL return an empty filter dict, allowing all titles through

### Requirement: scout.yaml title_filter removed
The `title_filter:` section SHALL be removed from `configs/scout.yaml` (and `scout.yaml` itself deleted). No other file SHALL duplicate the filter definition.

#### Scenario: Single source of truth for filters
- **WHEN** a user updates `positive` keywords
- **THEN** they SHALL only need to edit `profile.yaml`
