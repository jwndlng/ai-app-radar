# Specification: Evaluation Generic Baseline

## Purpose
Scoring weights and thresholds live in `configs/settings.yaml` under the `evaluate:` section (read by `AppConfigLoader` / `EvaluateSettings`). All personal values are sourced from `profile.yaml` at runtime.

## Requirements

### Requirement: settings.yaml evaluate section contains only scoring weights and thresholds
The `evaluate:` block in `configs/settings.yaml` SHALL contain only generic scoring machinery: weights and triage thresholds. All personal values (salary ranges, location strings, domain scores, tech keywords) SHALL be sourced from `profile.yaml` at runtime.

#### Scenario: evaluate section has no personal data
- **WHEN** `settings.yaml` is read by someone forking the tool
- **THEN** the `evaluate:` section SHALL contain no names, salary figures, locations, or technology preferences specific to any individual

#### Scenario: Scorer combines settings.yaml weights with profile.yaml values
- **WHEN** the evaluation scorer runs
- **THEN** it SHALL read scoring weights and thresholds from `settings.yaml` (`EvaluateSettings`) and personal match criteria from `profile.yaml`

### Requirement: Triage thresholds are configurable
The `auto_reject_threshold` and `auto_match_threshold` fields SHALL remain in `configs/settings.yaml` under `evaluate:` as configurable baselines.

#### Scenario: Thresholds present in settings.yaml
- **WHEN** `configs/settings.yaml` is read
- **THEN** it SHALL contain `auto_reject_threshold` and `auto_match_threshold` with sensible default values
