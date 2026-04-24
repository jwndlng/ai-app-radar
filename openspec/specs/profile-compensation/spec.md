# Specification: Profile Compensation

## Purpose
Compensation targets and currency live in `profile.yaml`, replacing hardcoded values in `evaluation.yaml` and enabling currency-aware salary comparison at evaluation time.

## Requirements

### Requirement: profile.yaml contains compensation targets with currency
`configs/profile.yaml` SHALL include a `compensation:` section specifying the candidate's target salary and `currency`, replacing hardcoded values in `evaluation.yaml`.

#### Scenario: Compensation section structure
- **WHEN** `profile.yaml` is read
- **THEN** `compensation` SHALL contain at minimum: `currency` (e.g. `"CHF"`), `target` (target salary in that currency), and `minimum` (floor below which roles are auto-rejected)

### Requirement: Evaluation normalises role salary to profile currency using exchange rates
The evaluation scorer SHALL convert the role's stored salary (from the enriched `salary_range` field) to the profile's `compensation.currency` using live or cached exchange rates before comparison.

#### Scenario: USD role evaluated against CHF target
- **WHEN** a role has a USD salary and `profile.yaml` specifies `currency: CHF`
- **THEN** the scorer SHALL convert the USD value to CHF before comparing against `compensation.target` and `compensation.minimum`

#### Scenario: Role with no salary range
- **WHEN** a role has no `salary_range`
- **THEN** the scorer SHALL skip compensation scoring for that role without error
