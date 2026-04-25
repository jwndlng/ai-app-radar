# Specification: Tuning Cases Capability

## Purpose
To define the format and storage conventions for tuning case files used by the tuning harness.

## Requirements

### Requirement: Case files are YAML documents in tuning/cases/
Each tuning case SHALL be a YAML file at `tuning/cases/<company-slug>.yaml` containing the company config, expected outcomes, and list of models to evaluate.

#### Scenario: Case file loaded by runner
- **WHEN** the runner is invoked with `CASE=google`
- **THEN** it SHALL load `tuning/cases/google.yaml` and fail with a clear error if the file does not exist

### Requirement: Case file schema
A case file SHALL contain the following fields:

- `company` (string, required): display name
- `careers_url` (string, required): URL passed to `WebsearchProvider`
- `scan_method_config` (object, optional): forwarded verbatim to the company config
- `expected.pages` (int, required): exact number of pages expected
- `expected.jobs_min` (int, required): minimum acceptable job count
- `expected.jobs_max` (int, required): maximum acceptable job count
- `models` (list of strings, required): model identifiers to evaluate

#### Scenario: Minimal valid case file
- **WHEN** a case file contains `company`, `careers_url`, `expected.pages`, `expected.jobs_min`, `expected.jobs_max`, and `models`
- **THEN** the runner SHALL accept it without error

#### Scenario: Missing required field
- **WHEN** a case file omits `models` or any `expected` subfield
- **THEN** the runner SHALL raise a validation error before making any network calls

### Requirement: Shipped case files include a representative free-model baseline

> **Note (backlog):** Case files committed to the repo should include a `models` list that covers free-tier and local options alongside paid models — e.g. `gemini/gemini-2.5-flash` (Gemini free tier), `groq/llama-3.3-70b-versatile` (Groq free tier), `ollama/gemma3:27b` (local) — so contributors without paid API access can run comparisons and the results give users a meaningful guide to model suitability for each pipeline stage.

### Requirement: tuning/results/ is excluded from version control
The `tuning/results/` directory SHALL be listed in `.gitignore`. Case files in `tuning/cases/` SHALL be committed.

#### Scenario: Results not tracked by git
- **WHEN** a tune run writes a result file to `tuning/results/`
- **THEN** git SHALL not stage or track the file
