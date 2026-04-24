# Specification: Scout Capability

## Purpose
To discover, filter, and ingest new job opportunities from configured portals into the `artifacts/applications.json` tracker.

## Requirements

### Requirement: Multi-Level Extraction
The scout SHALL implement a three-tiered discovery strategy:
1. **API Tier**: Direct JSON extraction from Greenhouse/Ashby APIs for supported companies.
2. **Scraper Tier**: Playwright-based navigation and extraction from `careers_url` of tracked companies.
3. **Search Tier**: Broad discovery via WebSearch queries for new or untracked companies.

### Requirement: Rule-Based Filtering
The scout SHALL filter discovered titles against the `positive` and `negative` keywords defined under `scout_filters:` in `profile.yaml` (loaded by `AppConfigLoader.scout()` in `src/core/config.py`).

#### Scenario: Relevant Role Discovery
- **WHEN** a role is found with "Security Engineer" in the title
- **THEN** it SHALL be accepted if no negative keywords (e.g., "Junior") are present.

### Requirement: Location & Logistics Vetting
The scout SHALL verify that the role matches the candidate's preferred locations (Zurich, Zug, Remote Europe/EMAS) as defined in the master metadata.

### Requirement: Atomic State Ingestion
Discovered roles SHALL be added to `artifacts/applications.json` in a deduplicated manner. Every job listing MUST include a `discovered_at` date.

#### Scenario: Unified Deduplication
- **WHEN** a role is found
- **THEN** it SHALL be silently skipped if the URL exists in `artifacts/applications.json` regardless of its current status.

### Requirement: Liveness Verification
For results originating from the **Search Tier**, the scout SHALL perform a liveness check using Playwright to confirm the role is still open.

### Requirement: Scout dispatches to ATS API providers for known platforms
The scout orchestrator SHALL handle `scan_method` values `ashby_api`, `lever_api`, and `workable_api` in its dispatch loop, routing each company config to the corresponding provider. This extends the existing dispatch without altering any existing path.

#### Scenario: ashby_api company is processed
- **WHEN** a tracked company has `scan_method: ashby_api`
- **THEN** the orchestrator SHALL call `AshbyProvider` and ingest the returned jobs via the existing `process_discovered` pipeline

#### Scenario: lever_api company is processed
- **WHEN** a tracked company has `scan_method: lever_api`
- **THEN** the orchestrator SHALL call `LeverProvider` and ingest via `process_discovered`

#### Scenario: workable_api company is processed
- **WHEN** a tracked company has `scan_method: workable_api`
- **THEN** the orchestrator SHALL call `WorkableProvider` and ingest via `process_discovered`

#### Scenario: WebsearchProvider accepts optional model override
- **WHEN** `WebsearchProvider` is constructed with an explicit `model` argument
- **THEN** it SHALL pass that model to `ScoutAgent` instead of reading `SCOUT_MODEL` from the environment
- **AND** existing call sites that omit the argument SHALL continue to work unchanged
