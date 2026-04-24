# Specification: ATS API Providers Capability

## Purpose

<!-- TBD: expand with full capability context -->
To fetch job listings from ATS platforms (Ashby, Lever, Workable) via their public JSON endpoints, normalising results and applying keyword filtering before returning them to the scout orchestrator.

## Requirements

### Requirement: ATS API providers fetch job listings via public JSON endpoints
Each ATS provider (Ashby, Lever, Workable) SHALL fetch job listings by calling a public JSON endpoint keyed by the company's `scan_slug`. All three providers SHALL follow the same contract: accept a company config entry, return a list of normalised job dicts with `title`, `url`, `company`, and `location` fields, and apply the global keyword filter before returning.

The endpoint per provider:
- **Ashby**: `https://jobs.ashbyhq.com/api/non-user-facing/job-board/named-account/jobs?organizationHostedJobsPageName={slug}`
- **Lever**: `https://api.lever.co/v0/postings/{slug}?mode=json`
- **Workable**: `https://apply.workable.com/api/v1/widget/accounts/{slug}/vacancies`

#### Scenario: Successful fetch returns filtered jobs
- **WHEN** the API returns a valid JSON response with job listings
- **THEN** the provider SHALL return only jobs whose titles match the global keyword filter, each with `title`, `url`, `company`, and `location` populated

#### Scenario: No jobs pass the keyword filter
- **WHEN** the API returns jobs but none match the keyword filter
- **THEN** the provider SHALL return an empty list without error

#### Scenario: API request fails — falls back to websearch
- **WHEN** the endpoint returns a non-200 response or a network error occurs
- **THEN** the provider SHALL log a warning and delegate to the `WebsearchProvider` for that company as a fallback, so the scout run always produces a best-effort result

### Requirement: Company slug is configurable independently of careers URL
A company config entry MAY include a `scan_slug` field. When present, the provider SHALL use it as the API identifier. When absent, the provider SHALL derive the slug from the last path segment of `careers_url`.

#### Scenario: Explicit scan_slug provided
- **WHEN** `scan_slug: "AlephAlpha"` is set and `careers_url` is `https://jobs.ashbyhq.com/AlephAlpha`
- **THEN** the provider SHALL use `"AlephAlpha"` as the slug without parsing the URL

#### Scenario: Slug derived from careers_url
- **WHEN** no `scan_slug` is set and `careers_url` is `https://jobs.ashbyhq.com/elevenlabs`
- **THEN** the provider SHALL derive `"elevenlabs"` from the URL path

### Requirement: scan_method values select the correct provider
The scout orchestrator SHALL dispatch to `AshbyProvider`, `LeverProvider`, or `WorkableProvider` based on `scan_method` values `ashby_api`, `lever_api`, and `workable_api` respectively.

#### Scenario: Ashby dispatch
- **WHEN** a company config has `scan_method: ashby_api`
- **THEN** the orchestrator SHALL call `AshbyProvider` with that config entry

#### Scenario: Lever dispatch
- **WHEN** a company config has `scan_method: lever_api`
- **THEN** the orchestrator SHALL call `LeverProvider` with that config entry

#### Scenario: Workable dispatch
- **WHEN** a company config has `scan_method: workable_api`
- **THEN** the orchestrator SHALL call `WorkableProvider` with that config entry
