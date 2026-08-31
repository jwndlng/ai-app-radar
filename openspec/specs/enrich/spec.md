# Specification: Enrich Capability

## Purpose
To extract structured, neutral facts from raw job descriptions into an `EnrichResult` model.
The enrich phase extracts objective job facts; evaluation applies candidate-specific judgment.

## Requirements

### Requirement: EnrichResult extracts a flat tech stack list
The `EnrichResult` model SHALL include a `tech_stack` field containing a flat list of named
technologies, tools, and frameworks explicitly mentioned in the job description.

The list SHALL contain specific names (e.g. `"Terraform"`, `"AWS"`, `"Python"`) rather than
prose descriptions. Generic terms ("cloud", "scripting") SHALL be omitted.

#### Scenario: JD mentioning specific tools produces a populated list
- **WHEN** the job description explicitly names technologies such as Python, Kubernetes, or Terraform
- **THEN** `tech_stack` SHALL contain those names as individual list entries

#### Scenario: JD with no explicit tools produces an empty list
- **WHEN** the job description contains no specific named technologies
- **THEN** `tech_stack` SHALL be an empty list

### Requirement: EnrichResult classifies job domains
The `EnrichResult` model SHALL include a `domains` field containing a list of high-level
technology or industry domain labels that describe what the role is objectively about,
independent of any candidate profile.

Example values: `"Cloud Security"`, `"AI Security"`, `"Blockchain"`, `"Web3"`, `"Fintech"`,
`"Detection Engineering"`, `"Infrastructure"`, `"Compliance"`.

#### Scenario: Security-focused AI role receives multiple domain labels
- **WHEN** a job description covers both AI/ML pipelines and security engineering
- **THEN** `domains` SHALL contain both `"AI Security"` and at least one other relevant label

#### Scenario: Single-domain role receives one label
- **WHEN** a job description is clearly scoped to one domain (e.g. network security only)
- **THEN** `domains` SHALL contain a single appropriate label

### Requirement: Scout-provided fields survive enrichment
Applying an `EnrichResult` to a job SHALL NOT overwrite the scout-provided `title`, `company`, or `location` with empty extraction output. A non-empty extracted value MAY replace the scout value; an empty one SHALL be ignored.

#### Scenario: Empty extracted location is ignored
- **WHEN** the extraction returns `location: ""` for a job whose scout record has `location: "Zurich"`
- **THEN** the job SHALL keep `location: "Zurich"` after enrichment

### Requirement: Failed enrichment attempts are bounded
Each failed fetch/extract attempt SHALL increment an `enrich_attempts` counter on the job. Jobs with 3 or more failed attempts SHALL be excluded from subsequent enrich runs (dead or expired listings must not consume fetch and LLM cost indefinitely). A successful enrichment SHALL clear the counter, and the repair flow's reset SHALL also clear it so a repaired job becomes eligible again.

#### Scenario: Repeatedly dead listing stops being retried
- **WHEN** a job has failed enrichment 3 times
- **THEN** the enrich producer SHALL skip it on subsequent runs

#### Scenario: Repair makes a failed job eligible again
- **WHEN** the repair flow resets a failed job
- **THEN** its `enrich_attempts` counter SHALL be cleared and the next enrich run SHALL include it
