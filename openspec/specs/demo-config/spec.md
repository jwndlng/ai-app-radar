# Capability: Demo Configuration

## Purpose

Ship example configuration files so new users can run the full pipeline immediately without entering personal data, while ensuring real user config files are never accidentally committed.

## Requirements

### Requirement: Demo profile ships with the repository
The repository SHALL include `configs/profile.example.yaml` containing a realistic but fictional candidate profile that new users can use to test the pipeline immediately without entering personal data.

#### Scenario: Example profile is runnable
- **WHEN** a user copies profile.example.yaml to profile.yaml and runs the pipeline
- **THEN** the pipeline produces meaningful output (scout, enrich, evaluate all work)

#### Scenario: Example profile uses a fictional persona
- **WHEN** a user inspects profile.example.yaml
- **THEN** the profile contains no real personal data — fictional name, email, and work history

### Requirement: Demo company list ships with the repository
The repository SHALL include `configs/companies.example.json` containing 10–15 real companies with verified ATS configurations that new users can use as a starter set.

#### Scenario: Example companies are immediately usable
- **WHEN** a user copies companies.example.json to companies.json and runs scout
- **THEN** at least some companies return live job listings without further configuration

#### Scenario: Example covers multiple ATS providers
- **WHEN** a user inspects companies.example.json
- **THEN** entries span at least three ATS providers (e.g. Greenhouse, Ashby, Lever)

### Requirement: User config files are gitignored
`configs/profile.yaml` and `configs/companies.json` SHALL be listed in `.gitignore` so that users' real personal data is never accidentally committed to a fork or contribution.

#### Scenario: Real config files are ignored by git
- **WHEN** a user creates configs/profile.yaml with personal data
- **THEN** `git status` does not show that file as tracked or staged

### Requirement: Personal data is removed from source code
`src/core/logger.py` SHALL NOT contain hardcoded references to the author's employer (DFINITY) in examples or doctests.

#### Scenario: Logger example uses a generic company name
- **WHEN** a developer reads src/core/logger.py
- **THEN** any example output uses a placeholder company name, not "DFINITY"
