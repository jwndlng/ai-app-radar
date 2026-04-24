## Purpose

Specification for the `/app:onboard-company` Claude Code skill that classifies a company's careers page ATS, verifies the config is live, and appends a correctly structured entry to `configs/companies.json`.

## Requirements

### Requirement: Skill accepts company name and careers URL as input
The skill SHALL accept a company name as a required input and a careers page URL as an **optional** input.

#### Scenario: Both inputs provided
- **WHEN** the user invokes `/app:onboard-company` with a company name and careers URL
- **THEN** the skill proceeds directly to ATS classification (skips discovery)

#### Scenario: Only company name provided
- **WHEN** the user invokes `/app:onboard-company` with only a company name
- **THEN** the skill SHALL run careers-page discovery before proceeding to ATS classification

#### Scenario: Input missing
- **WHEN** the user invokes the skill without a company name
- **THEN** the skill asks the user to supply the company name before proceeding

### Requirement: ATS classification from URL pattern
The skill SHALL classify the ATS provider by inspecting the careers URL hostname and path, mapping known patterns to their corresponding `scan_method`.

Known ATS URL patterns and their `scan_method`:
| URL pattern | `scan_method` | slug source |
|---|---|---|
| `jobs.ashbyhq.com/<slug>` | `ashby_api` | path segment after `/` |
| `app.ashbyhq.com/<slug>` | `ashby_api` | path segment after `/` |
| `boards.greenhouse.io/<slug>` | `greenhouse_api` | path segment after `/` |
| `jobs.lever.co/<slug>` | `lever_api` | path segment after `/` |
| `apply.workable.com/<slug>` | `workable_api` | path segment after `/` |
| anything else | `agent_review` | omitted |

#### Scenario: Ashby URL detected
- **WHEN** the careers URL hostname is `jobs.ashbyhq.com` or `app.ashbyhq.com`
- **THEN** `scan_method` is set to `ashby_api` and `scan_slug` is the first path segment

#### Scenario: Greenhouse URL detected
- **WHEN** the careers URL hostname is `boards.greenhouse.io`
- **THEN** `scan_method` is set to `greenhouse_api` and `scan_slug` is the first path segment

#### Scenario: Lever URL detected
- **WHEN** the careers URL hostname is `jobs.lever.co`
- **THEN** `scan_method` is set to `lever_api` and `scan_slug` is the first path segment

#### Scenario: Workable URL detected
- **WHEN** the careers URL hostname is `apply.workable.com`
- **THEN** `scan_method` is set to `workable_api` and `scan_slug` is the first path segment

#### Scenario: Unknown / custom URL
- **WHEN** the careers URL does not match any known ATS pattern
- **THEN** `scan_method` is set to `agent_review`, no `scan_slug` is added, and the skill notes that no provider is known for this URL

### Requirement: Entry verification before writing
The skill SHALL verify the derived config is functional before appending to `configs/companies.json`.

For known ATS methods (`ashby_api`, `lever_api`, `workable_api`, `greenhouse_api`), verification means making a real API call to the provider endpoint and confirming a non-error HTTP response.

For `agent_review`, verification means issuing an HTTP HEAD or GET request to the careers URL and confirming a 2xx response.

#### Scenario: API verification succeeds
- **WHEN** the test API call to the provider returns HTTP 2xx
- **THEN** the skill proceeds to append the entry to `configs/companies.json`

#### Scenario: API verification fails for known ATS
- **WHEN** the test API call returns an error or the slug resolves to 404
- **THEN** the skill reports the failure, suggests checking the slug, and does NOT write to `configs/companies.json`

#### Scenario: URL reachability check for agent_review
- **WHEN** a GET request to the careers URL returns HTTP 2xx
- **THEN** the skill proceeds to append the entry

#### Scenario: URL unreachable for agent_review
- **WHEN** the careers URL is unreachable or returns a non-2xx response
- **THEN** the skill reports the failure and does NOT write to `configs/companies.json`

### Requirement: Metadata enrichment during onboarding
After ATS classification, the skill SHALL infer `category` from the company name and careers URL using an LLM, and prompt the user to confirm or override. The skill SHALL also prompt for `employees` headcount band.

#### Scenario: Category inferred and confirmed
- **WHEN** the LLM infers a category (e.g. `"fintech"`) for the company
- **THEN** the skill SHALL display the inferred category and ask the user to confirm, override, or skip

#### Scenario: Category unknown
- **WHEN** the LLM cannot confidently infer a category
- **THEN** the skill SHALL prompt the user to enter a category manually or skip (leaving the field absent)

#### Scenario: Employees prompt
- **WHEN** onboarding a company
- **THEN** the skill SHALL prompt for an employees headcount band (e.g. `"10-50"`, `"50-200"`, `"500+"`) and include it in the entry if provided; skip if the user leaves it blank

### Requirement: Append validated entry to companies.json
The skill SHALL append a correctly structured JSON entry to the `companies` array in `configs/companies.json` after successful verification.

The entry MUST include:
- `name`: the company name as provided
- `careers_url`: the careers URL as provided
- `scan_method`: derived from ATS classification
- `scan_method_config`: object with `slug` key for known ATS providers (omitted for `agent_review`)
- `enabled: true`
- `category`: inferred or user-provided (omitted if skipped)
- `employees`: user-provided (omitted if skipped)

The entry MUST NOT be appended if verification failed.

#### Scenario: Entry written for known ATS
- **WHEN** verification succeeds for a known ATS
- **THEN** the entry with `name`, `careers_url`, `scan_method`, `scan_method_config: {slug: "<slug>"}`, `enabled: true`, and any metadata is appended to `companies` in `configs/companies.json`

#### Scenario: Entry written for agent_review
- **WHEN** verification succeeds for an unknown ATS
- **THEN** the entry with `name`, `careers_url`, `scan_method: "agent_review"`, `enabled: true`, and any metadata is appended, with no `scan_method_config`

#### Scenario: Duplicate company name
- **WHEN** a company with the same name already exists in `configs/companies.json`
- **THEN** the skill warns the user and asks whether to replace the existing entry or abort

### Requirement: Summary output after onboarding
The skill SHALL print a concise summary after completing (or aborting) onboarding.

#### Scenario: Successful onboarding
- **WHEN** the entry is written to `configs/companies.json`
- **THEN** the skill prints the company name, detected ATS, derived `scan_method`, slug (if any), `category`, `employees`, and confirmation that the entry was added

#### Scenario: Onboarding aborted
- **WHEN** verification fails or the user aborts due to a duplicate
- **THEN** the skill explains what happened and what the user can do next (e.g., check the slug manually, try a different URL)

### Requirement: Batch onboarding skill
A `/app:batch-onboard` skill SHALL process multiple companies through the same discovery + classify + write flow as `/app:onboard-company`, operating on either:
- A list of company names passed as input, or
- All entries in `configs/companies.json` matching `--source <value>` that have `enabled == false` and no `status` set

The skill SHALL process entries in batches of 20 (configurable via `--batch N`), writing `configs/companies.json` after each entry. It SHALL skip entries that already have `status` set.

#### Scenario: Batch by source
- **WHEN** the skill is invoked with `--source zurich_valley`
- **THEN** it SHALL process up to the batch limit of entries where `source == "zurich_valley"`, `enabled == false`, and no `status` is set

#### Scenario: Any source value supported
- **WHEN** the skill is invoked with `--source <any_value>`
- **THEN** it SHALL filter by that source value, making the mechanism reusable for any future bulk import

#### Scenario: Batch from name list
- **WHEN** the skill is invoked with a list of company names
- **THEN** it SHALL run the full onboard flow for each name and append results to `configs/companies.json`

#### Scenario: Batch interrupted mid-run
- **WHEN** the session ends before the batch is complete
- **THEN** all entries processed before interruption SHALL already be persisted; resuming runs the skill again to continue

#### Scenario: Progress summary
- **WHEN** a batch completes
- **THEN** the skill SHALL print counts: enabled (success), needs_manual_review, ats_unsupported, and entries with the given source still remaining
