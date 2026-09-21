## ADDED Requirements

### Requirement: Configurable rejected-job age threshold
The system SHALL expose an `archival.rejected_after_days` setting in `configs/settings.yaml`, loaded into `ArchivalSettings.rejected_after_days` (default `30`) via `AppConfigLoader`.

#### Scenario: Default threshold applied when unset
- **WHEN** `configs/settings.yaml` has no `archival` section
- **THEN** `AppConfigLoader.settings().archival.rejected_after_days` SHALL be `30`

#### Scenario: Custom threshold applied when set
- **WHEN** `configs/settings.yaml` contains `archival: { rejected_after_days: 60 }`
- **THEN** `AppConfigLoader.settings().archival.rejected_after_days` SHALL be `60`

### Requirement: Failed jobs are cleaned up on their own threshold
The system SHALL expose `archival.failed_after_days` (default `60`) in `configs/settings.yaml`. Jobs whose `status` is `"failed"` and whose age exceeds this threshold SHALL be archived by `JobArchiver` regardless of state, using the same archive-then-delete flow. Failed-job age SHALL be computed from `failed_at` (stamped when a job is marked failed) when present, so a fresh failure on an old record is not archived prematurely. Passing `failed_after_days=None` to `JobArchiver` disables failed-job cleanup.

#### Scenario: Old failed job is archived
- **WHEN** `JobArchiver.run()` is called with `failed_after_days=60` and a job has `status: "failed"` with age over 60 days
- **THEN** the job SHALL be moved to the archive file and removed from the active store

#### Scenario: Recently failed job is retained
- **WHEN** a failed job's age is within the threshold
- **THEN** it SHALL remain in the active store (it may still be repaired and retried)

### Requirement: Archive old rejected jobs out of the active store
The system SHALL provide a `JobArchiver` that moves jobs whose `state` is `"rejected"` (location hard-block, stamped `vetted_at`) or `"archived"` (score-based auto-reject, stamped `archived_at`) — both terminal, no-future-value outcomes — out of `artifacts/applications.json` into `artifacts/applications_archive.json` once their age exceeds the configured `rejected_after_days` threshold. Age SHALL be computed from `archived_at`, falling back to `vetted_at`, falling back to `updated_at`. Jobs lacking all three timestamps SHALL be left in place (not archived).

#### Scenario: Old rejected job is archived
- **WHEN** `JobArchiver.run()` is called and a job has `state: "rejected"` and `vetted_at` older than the configured threshold
- **THEN** the job SHALL be removed from `applications.json` and present in `applications_archive.json` after the run

#### Scenario: Recently rejected job is not archived
- **WHEN** `JobArchiver.run()` is called and a job has `state: "rejected"` with `vetted_at` within the configured threshold
- **THEN** the job SHALL remain in `applications.json` and SHALL NOT appear in `applications_archive.json`

#### Scenario: Old auto-rejected (archived-state) job is archived
- **WHEN** `JobArchiver.run()` is called and a job has `state: "archived"` and `archived_at` older than the configured threshold
- **THEN** the job SHALL be removed from `applications.json` and present in `applications_archive.json` after the run

#### Scenario: Recently auto-rejected (archived-state) job is not archived
- **WHEN** `JobArchiver.run()` is called and a job has `state: "archived"` with `archived_at` within the configured threshold
- **THEN** the job SHALL remain in `applications.json` and SHALL NOT appear in `applications_archive.json`

#### Scenario: Non-terminal jobs are never archived
- **WHEN** `JobArchiver.run()` is called and a job has any `state` other than `"rejected"` or `"archived"` (e.g. `"match"`, `"applied"`, `"review"`), regardless of age
- **THEN** the job SHALL remain in `applications.json` and SHALL NOT be moved

#### Scenario: Missing timestamp leaves job in place
- **WHEN** `JobArchiver.run()` is called and a rejected or archived job has none of `archived_at`, `vetted_at`, or `updated_at`
- **THEN** the job SHALL remain in `applications.json`

#### Scenario: Fallback to updated_at when no other timestamp is present
- **WHEN** `JobArchiver.run()` is called and a rejected job has no `vetted_at` but has an `updated_at` older than the configured threshold
- **THEN** the job SHALL be archived

#### Scenario: Archive file accumulates across runs
- **WHEN** `JobArchiver.run()` is called and `applications_archive.json` already contains previously archived jobs
- **THEN** the newly archived jobs SHALL be appended to the existing archive contents, not overwrite them

#### Scenario: No-op when nothing qualifies
- **WHEN** `JobArchiver.run()` is called and no job qualifies for archival
- **THEN** neither `applications.json` nor `applications_archive.json` SHALL be written, and `run()` SHALL return `0`

#### Scenario: Archive is written before jobs are deleted
- **WHEN** `JobArchiver.run()` archives qualifying jobs
- **THEN** the archive file write SHALL complete before any job is deleted from the active store, so a failed write cannot lose jobs permanently

#### Scenario: Corrupt archive file is preserved, not overwritten
- **WHEN** the existing `applications_archive.json` cannot be parsed
- **THEN** it SHALL be moved aside (e.g. `.corrupt` suffix) and a fresh archive written; the unreadable content SHALL NOT be silently overwritten. Archive writes SHALL go through a temp file and atomic rename.

#### Scenario: Manual rejection restarts the archival clock
- **WHEN** a job is manually rejected via the API
- **THEN** `vetted_at` SHALL be stamped with the rejection time, so archival counts from the rejection, not from the original evaluation

#### Scenario: Naive timestamps are interpreted as local time
- **WHEN** a job timestamp lacks timezone information
- **THEN** age computation SHALL treat it as local time (pipeline stamps are naive local), not UTC

### Requirement: Archival runs automatically as part of sync
The `sync` flow (`PipelineCLI._run_sync`) SHALL invoke `JobArchiver.run()` as a final step after scout, enrich, and evaluate complete. A failure during archival SHALL be caught and printed as a warning, and SHALL NOT cause `sync` to exit with a non-zero status or discard the results of the preceding scout/enrich/evaluate steps.

#### Scenario: Archival runs after evaluate on a normal sync
- **WHEN** `sync` is run and scout, enrich, and evaluate all complete successfully
- **THEN** `JobArchiver.run()` SHALL be invoked before `sync` reports completion

#### Scenario: Archival failure does not fail sync
- **WHEN** `JobArchiver.run()` raises an exception during a `sync` run
- **THEN** `sync` SHALL print a warning and still exit successfully, with scout/enrich/evaluate results intact

#### Scenario: Standalone scout/enrich/evaluate runs do not trigger archival
- **WHEN** `scout`, `enrich`, or `evaluate` is run individually (not via `sync`)
- **THEN** `JobArchiver.run()` SHALL NOT be invoked
