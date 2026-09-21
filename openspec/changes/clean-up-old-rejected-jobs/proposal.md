## Why

`applications.json` (managed by `ApplicationStore`) accumulates every job the scout has ever discovered, including jobs that were auto-rejected by the evaluate flow. Rejected jobs carry no future value once they're old enough that the company has likely filled or removed the role, but today nothing ever removes them — the store only grows. This bloats the active dataset the API and dashboard load on every request, and makes it harder to spot genuinely fresh activity. We need an automatic, configurable way to move old rejected jobs out of the active store.

## What Changes

- Add a cleanup step that archives rejected jobs older than a configurable threshold out of `applications.json` into a separate archive file, preserving history instead of deleting it.
- The age threshold is based on the job's `vetted_at` (fallback `updated_at`) timestamp and is configurable via `configs/settings.yaml` (with a sensible default), not hardcoded.
- The cleanup step runs automatically as part of the existing `sync` flow (scout → enrich → evaluate), after evaluate completes — no new standalone CLI command is introduced.
- Archived jobs are written to a new file, `artifacts/applications_archive.json`, appended to (not overwritten) on each run.

## Capabilities

### New Capabilities
- `rejected-job-archival`: Automatic, configurable archival of old rejected jobs from the active application store into a separate archive file, run as part of the `sync` pipeline.

### Modified Capabilities
(none — `sync`'s existing scout/enrich/evaluate behavior is unchanged; this only adds a step after it)

## Impact

- **Code**: `src/cli.py` (`_run_sync`, add archival step), likely new module e.g. `src/maintenance/archival.py`, `src/core/store.py` (may need a method to split/filter jobs), `src/core/config.py` (new `ArchivalConfig`/settings).
- **Config**: `configs/settings.yaml` gains a new section (e.g. `archival.rejected_after_days`).
- **Data**: New file `artifacts/applications_archive.json`; `artifacts/applications.json` shrinks over time as old rejected jobs move out.
- **Dependencies**: None new.
