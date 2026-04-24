## Purpose

Specification for the company discovery procedure that, given a company name, locates and returns a verified careers page URL suitable for ATS detection and onboarding.

## Requirements

### Requirement: Careers page discovery from company name
The discovery procedure SHALL accept a company name and optional domain hint, and return a verified careers page URL.

#### Scenario: Discovery via web search
- **WHEN** a web search for `"<company name>" careers jobs` returns a result matching a known ATS pattern or a path under the company domain
- **THEN** the procedure SHALL return that URL as the careers URL

#### Scenario: Discovery via homepage scrape
- **WHEN** web search returns no clear careers URL
- **THEN** the procedure SHALL fetch the company homepage and scan all `<a href>` links for text matching `careers`, `jobs`, `we're hiring`, `open positions`, or `join us` (case-insensitive), and return the first match

#### Scenario: Discovery fails
- **WHEN** neither web search nor homepage scrape yields a valid careers URL
- **THEN** the procedure SHALL return no URL; the caller SHALL flag the entry as `status: "needs_manual_review"`

### Requirement: ATS detection from URL
Given a careers URL, the detection procedure SHALL classify the ATS provider and return `scan_method` and `scan_method_config`.

Known patterns:
| URL pattern | `scan_method` | `scan_method_config` |
|---|---|---|
| `jobs.ashbyhq.com/<slug>` | `ashby_api` | `{slug: "<slug>"}` |
| `app.ashbyhq.com/<slug>` | `ashby_api` | `{slug: "<slug>"}` |
| `boards.greenhouse.io/<slug>` | `greenhouse_api` | `{api_base: "https://boards-api.greenhouse.io/v1/boards/<slug>/jobs"}` |
| `jobs.lever.co/<slug>` | `lever_api` | `{slug: "<slug>"}` |
| `apply.workable.com/<slug>` | `workable_api` | `{slug: "<slug>"}` |
| anything else | `agent_review` | (none) |

#### Scenario: Known ATS detected
- **WHEN** the careers URL matches a known ATS hostname
- **THEN** the procedure SHALL return the correct `scan_method` and `scan_method_config`

#### Scenario: Unsupported ATS detected
- **WHEN** the careers URL points to an ATS not in the known list (e.g. Workday, SmartRecruiters)
- **THEN** `scan_method` SHALL be `agent_review` and the entry SHALL receive `status: "ats_unsupported"` for future follow-up
