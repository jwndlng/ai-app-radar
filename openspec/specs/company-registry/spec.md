## Purpose

Specification for the company registry — the `configs/companies.json` file that stores all company entries, their scout configuration, and enrichment metadata.

## Requirements

### Requirement: Single flat JSON company registry
The system SHALL store all tracked companies in a single file `configs/companies.json` containing a top-level `companies` array. The per-category YAML files under `configs/companies/` SHALL be deleted.

#### Scenario: All companies in one file
- **WHEN** `configs/companies.json` is read
- **THEN** it SHALL contain a single `companies` array with all tracked entries

#### Scenario: YAML files absent after migration
- **WHEN** `configs/companies/` directory is checked after migration
- **THEN** it SHALL not exist or be empty — `configs/companies.json` is the sole source

### Requirement: Company entry schema
Each entry in the `companies` array SHALL contain:
- `name` (string, required): company display name
- `careers_url` (string, required): URL of the careers page or ATS job listing
- `scan_method` (string, required): one of `agent_review`, `greenhouse_api`, `lever_api`, `ashby_api`, `workable_api`
- `scan_method_config` (object, optional): method-specific config replacing ad-hoc `scan_slug`, `scan_query`, `api` fields
- `enabled` (boolean, required): whether this company is actively scouted
- `category` (string, optional): informational domain tag (e.g. `"AI/ML"`, `"Fintech"`)
- `employees` (string, optional): headcount band (e.g. `"50-200"`, `"500+"`)

#### Scenario: Minimal required entry
- **WHEN** an entry contains only `name`, `careers_url`, `scan_method`, and `enabled`
- **THEN** the scout SHALL process it without error

#### Scenario: Full entry with config
- **WHEN** an entry includes `scan_method_config` (e.g. `{"slug": "lakera"}`)
- **THEN** the scout provider SHALL read the slug from `scan_method_config.slug`

### Requirement: scan_method_config replaces ad-hoc scan fields
The fields `scan_slug`, `scan_query`, and `api` SHALL NOT appear as top-level entry fields. Their values SHALL be moved into `scan_method_config` sub-keys: `slug`, `query`, and `api_base` respectively.

#### Scenario: Greenhouse slug migration
- **WHEN** a previous entry had `scan_slug: "lakera"`
- **THEN** the migrated entry SHALL have `scan_method_config: {slug: "lakera"}`

### Requirement: location field removed from company entries
Company entries SHALL NOT contain a `location` field. Location filtering applies to job postings (via `profile.yaml` `location_preferences`), not to company records.

#### Scenario: Migrated entries have no location field
- **WHEN** any entry from `configs/companies.json` is read
- **THEN** it SHALL NOT contain a `location` key

### Requirement: Zurich Valley companies imported
All companies from `artifacts/zurichvalley_companies.json` SHALL be imported into `configs/companies.json` with `scan_method: "agent_review"` and `enabled: true`. The source `cat` field maps to `category` and `employees` maps directly.

#### Scenario: Import maps metadata fields
- **WHEN** a Zurich Valley entry with `cat: "Fintech"` and `employees: "500+"` is imported
- **THEN** the resulting entry SHALL have `category: "Fintech"` and `employees: "500+"`

#### Scenario: Duplicates not imported
- **WHEN** a company name (case-insensitive) already exists in `configs/companies.json`
- **THEN** the existing entry SHALL be preserved unchanged and the ZV entry skipped

### Requirement: Company entries support optional metadata fields
Each company entry in `configs/companies.json` MAY include `category`, `employees`, `source`, and `status` fields. These fields are informational and SHALL NOT affect scout behavior except where noted.

#### Scenario: Entry with provenance and status
- **WHEN** a company entry includes `source: "zurich_valley"` and `status: "needs_manual_review"`
- **THEN** the scout SHALL skip it (it remains `enabled: false`)

#### Scenario: Entry without metadata
- **WHEN** a company entry omits `source`, `status`, `category`, and `employees`
- **THEN** the scout SHALL process it without error

### Requirement: source field tracks entry provenance
Company entries MAY include a `source` field indicating how they were added:
- `"zurich_valley"`: imported from `artifacts/zurichvalley_companies.json`
- Absent: manually onboarded via `/app:onboard-company` or present from the original YAML migration

#### Scenario: Source field on ZV import
- **WHEN** an entry was imported from the Zurich Valley dataset
- **THEN** it SHALL have `source: "zurich_valley"` until enrichment removes it or it is manually confirmed

### Requirement: status field tracks enrichment state
Company entries MAY include a `status` field:
- `"needs_manual_review"`: careers page could not be discovered automatically
- `"ats_unsupported"`: careers page found but ATS is not a supported provider
- Absent: entry is fully configured and active

#### Scenario: Manual review flag preserved across runs
- **WHEN** an entry has `status: "needs_manual_review"`
- **THEN** the enrichment skill SHALL skip it on subsequent runs
