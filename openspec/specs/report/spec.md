# Specification: Report Capability

## Purpose
To provide a repeatable and discoverable mechanism for transforming the "Application as Code" artifacts into prioritized, human-readable triage dashboards.

## Requirements

### Requirement: Slash-Command Discovery
The system SHALL expose the report generation flow via a `/app-report` workflow trigger for discoverability within the agentic environment.

### Requirement: CLI Portability
The system SHALL provide a standalone `bin/app-report` executable to allow for terminal-based generation outside of the agent context.

### Requirement: High-Rigor Data Aggregation
The report generator SHALL source data from the unified `artifacts/applications.json` registry to provide a holistic view of the discovery pipeline. The resulting dashboard MUST be written to `artifacts/dashboard.html`.

### Requirement: Dashboard Card Rendering
The dashboard SHALL render a card for each job that exposes all evaluation output produced by
the pipeline, making the LLM's scoring decision fully auditable without leaving the dashboard.

Each card SHALL display:
- Score as `N/10` (e.g. `7.5/10`) — never as a percentage
- Role archetype label
- Reasons: bulleted list of LLM-produced justification strings
- Tech stack tags: one pill tag per entry in `tech_stack`; tags whose value matches a profile
  skill SHALL use the accent-primary background (matched); all others SHALL use a muted style
- Domains tags: one pill tag per entry in `domains`
- Remote policy: single text value

The card SHALL NOT render any stale fields that no longer exist on job records:
`pros`, `cons`, `infrastructure_depth`, `builder_auditor_ratio`, `ai_agentic_security`,
`paved_roads_potential`.

Tag styles SHALL be defined in `CSS_TOKENS` in `templates.py`:
- `.tag` — base pill: small rounded, muted background, secondary text color
- `.tag-matched` — extends `.tag`: accent-primary background, white text

#### Scenario: Score displayed as N/10
- **WHEN** the dashboard renders a job card with a numeric score
- **THEN** the score SHALL be shown as `{score}/10` (e.g. `7.5/10`), not as a percentage

#### Scenario: Reasons rendered as bullet list
- **WHEN** the job record has a non-empty `reasons` list
- **THEN** each reason SHALL be rendered as a list item inside the expanded card

#### Scenario: Matched tech stack tag highlighted
- **WHEN** a `tech_stack` entry's lowercase value matches any skill in the profile `skill_tiers`
- **THEN** that tag SHALL render with the `.tag-matched` CSS class (accent background)

#### Scenario: Unmatched tech stack tag shown in muted style
- **WHEN** a `tech_stack` entry does not match any profile skill
- **THEN** that tag SHALL render with the base `.tag` CSS class

#### Scenario: Domains rendered as tags
- **WHEN** the job record has a non-empty `domains` list
- **THEN** each domain SHALL be rendered as a `.tag` pill in the card

#### Scenario: Card renders gracefully when fields are absent
- **WHEN** a job record has no `tech_stack`, `domains`, `reasons`, or `archetype`
- **THEN** those sections SHALL be omitted or show a graceful empty state — no rendering errors

#### Scenario: Stale fields not rendered
- **WHEN** the dashboard renders any job card
- **THEN** `pros`, `cons`, `infrastructure_depth`, `builder_auditor_ratio`,
  `ai_agentic_security`, and `paved_roads_potential` SHALL NOT appear in the output HTML
