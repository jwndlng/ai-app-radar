# Specification: Master Metadata

## Purpose
Establishing a structured Source of Truth (SoT) to power agentic discovery and evaluation flows.

## Requirements

### Requirement: Master Profile Integrity
The `profile.yaml` SHALL store a normalized version of the candidate's professional history, skills, and narrative.

#### Scenario: Full extraction from LaTeX
- **WHEN** the `profile.yaml` is initially seeded
- **THEN** it SHALL contain all professional experience entries from high-rigor resume sources.

### Requirement: Scout Rule Filtering
The `profile.yaml` SHALL provide clear filters (positive/negative) under `scout_filters:` to automate discovery triage.

#### Scenario: Filter-based Triage
- **WHEN** a role is discovered by `scout`
- **THEN** it SHALL be rejected if any "negative" keyword is present in the title.

### Requirement: Quantitative Evaluation Rubric
Scoring weights and thresholds are defined in `configs/settings.yaml` under the `evaluate:` section (read by `AppConfigLoader` / `EvaluateSettings`).

#### Scenario: Multi-dimensional scoring
- **WHEN** a Job Description is evaluated
- **THEN** it SHALL be assigned scores for Tech Fit, Role alignment, Logistics, and Mission.
