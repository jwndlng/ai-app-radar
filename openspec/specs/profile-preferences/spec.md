# Specification: Profile Preferences

## Purpose
Location preferences and mission domain fit scores live in profile.yaml, making the evaluation scorer generic and user-agnostic.

## Requirements

### Requirement: profile.yaml contains location preferences
`configs/profile.yaml` SHALL include a `location_preferences:` section listing accepted locations and remote policies, replacing the hardcoded location filters in `evaluation.yaml`.

#### Scenario: Location preferences structure
- **WHEN** `profile.yaml` is read
- **THEN** `location_preferences` SHALL contain a list of accepted values (e.g. `["Zurich", "Zug", "Remote Europe", "Remote EMEA"]`) and a `remote_eligible: true/false` flag

#### Scenario: Scorer reads location from profile
- **WHEN** the evaluation scorer checks a role's location
- **THEN** it SHALL compare against `profile.yaml` `location_preferences` rather than hardcoded strings in `evaluation.yaml`

### Requirement: profile.yaml contains mission domain preferences
`configs/profile.yaml` SHALL include a `mission_domains:` section mapping domain names to fit scores, replacing the domain scores hardcoded in `evaluation.yaml`.

#### Scenario: Mission domain fit scores in profile
- **WHEN** `profile.yaml` is read
- **THEN** `mission_domains` SHALL be a mapping of domain name to score, e.g. `ai_security: 10`, `cloud_infrastructure: 7`

#### Scenario: Scorer reads domain scores from profile
- **WHEN** the evaluation scorer classifies a role's `mission_domain`
- **THEN** it SHALL look up the score from `profile.yaml` `mission_domains` rather than `evaluation.yaml`
