# Specification: Company Metadata Schema

## Purpose
Company entries in `configs/companies.json` support optional metadata fields for richer company context without affecting scout behavior.

## Requirements

### Requirement: Company entries support optional metadata fields
Each company entry in `configs/companies.json` MAY include `category` and `employees` fields. These fields are informational and SHALL NOT affect scout behavior. The `location` field is removed.

#### Scenario: Entry with metadata
- **WHEN** a company entry includes `category` and `employees`
- **THEN** the scout SHALL process it identically to an entry without those fields

#### Scenario: Entry without metadata
- **WHEN** a company entry omits `category` and `employees`
- **THEN** the scout SHALL process it without error

### Requirement: Metadata fields follow the Zurich Valley registry schema
The optional fields SHALL align with the fields available in `artifacts/zurichvalley_companies.json`:
- `category` (string): domain category, e.g. `"Fintech"`, `"AI/ML"`, `"Cloud"`
- `employees` (string): headcount band, e.g. `"500+"`, `"10-50"`

#### Scenario: zurich_valley entries populated from dump
- **WHEN** entries from `artifacts/zurichvalley_companies.json` are imported into `configs/companies.json`
- **THEN** the `category` and `employees` fields from the JSON SHALL map directly to the company entry fields
