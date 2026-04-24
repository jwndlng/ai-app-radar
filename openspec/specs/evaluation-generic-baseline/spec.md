# Specification: Evaluation Generic Baseline

## Purpose
evaluation.yaml is a generic, forkable baseline containing only scoring weights and thresholds. All personal values are sourced from profile.yaml at runtime.

## Requirements

### Requirement: evaluation.yaml contains only scoring weights and thresholds
`configs/evaluation.yaml` SHALL contain only generic scoring machinery: vector weights, triage thresholds, and scoring logic descriptions. All personal values (salary ranges, location strings, domain scores, tech keywords) SHALL be removed and sourced from `profile.yaml` at runtime.

#### Scenario: evaluation.yaml has no personal data
- **WHEN** `evaluation.yaml` is read by someone forking the tool
- **THEN** it SHALL contain no names, salary figures, locations, or technology preferences specific to any individual

#### Scenario: Scorer combines evaluation.yaml weights with profile.yaml values
- **WHEN** the evaluation scorer runs
- **THEN** it SHALL read scoring weights and thresholds from `evaluation.yaml` and personal match criteria from `profile.yaml`

### Requirement: evaluation.yaml triage thresholds are preserved
The `triage_thresholds` block (`auto_reject`, `manual_review`, `auto_match`) SHALL remain in `evaluation.yaml` as a configurable baseline.

#### Scenario: Thresholds unchanged after refactor
- **WHEN** the refactor is applied
- **THEN** `evaluation.yaml` SHALL still contain `triage_thresholds` with the same default values
