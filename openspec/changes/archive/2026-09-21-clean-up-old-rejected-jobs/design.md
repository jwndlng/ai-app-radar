## Context

`ApplicationStore` (`src/core/store.py`) persists every job ever seen by the pipeline as a flat list in `artifacts/applications.json`. `EvaluateConsumer` (`src/evaluate/consumer.py`) has two distinct terminal auto-reject paths: `_reject_job()` sets `state: "rejected"` (location hard-block) and stamps `vetted_at`; `_archive_job()` sets `state: "archived"` (score below the auto-reject threshold — the common case) and stamps `archived_at`. Both are dead-end, no-future-value outcomes in practice. Nothing currently removes either — the file only grows. `sync` (`src/cli.py::_run_sync`) already runs scout → enrich → evaluate as a fixed sequence and is the natural place to add a final archival step, mirroring how `RepairOrchestrator` and other maintenance-style flows are simple orchestrator classes (not producer/consumer pipeline tasks) operating directly on `ApplicationStore`.

**Correction (post-deploy):** the initial implementation only checked `state == "rejected"`, missing the much more common `state == "archived"` auto-reject path entirely — old auto-rejected jobs never got archived. Fixed to treat both states as archival candidates.

## Goals / Non-Goals

**Goals:**
- Automatically move rejected jobs older than a configurable threshold out of `applications.json` into a separate archive file.
- Make the age threshold configurable via `configs/settings.yaml`, with a sensible default, following the existing `AppSettings`/`AppConfigLoader` pattern.
- Run the step automatically at the end of `sync`, with no new CLI command.
- Preserve archived jobs (no permanent deletion) so history isn't lost.

**Non-Goals:**
- Archiving jobs in any state other than `rejected` (e.g. `archived`, `applied`) — out of scope for this change.
- Exposing archived jobs through the API or dashboard UI.
- Restoring/un-archiving jobs (no restore path is being built).
- Adding a standalone `cleanup` CLI flow — explicitly rejected in favor of running inside `sync`.

## Decisions

**1. New `ArchivalConfig` + `ArchivalSettings` in `core/config.py`, following the existing per-flow pattern.**
Add `ArchivalSettings(rejected_after_days: int = 30)` to `AppSettings`, loaded from a new `archival:` section in `configs/settings.yaml`. This matches how `scout`/`enrich`/`evaluate` settings are already structured — no new config-loading mechanism needed.

**2. New `JobArchiver` class in a new module `src/maintenance/archiver.py`.**
Alternatives considered: adding archival logic directly to `ApplicationStore`, or bolting it onto `RepairOrchestrator`. Rejected both — `ApplicationStore` is a pure persistence layer (load/save/migrate) and shouldn't know about business rules like "what counts as old"; `RepairOrchestrator` is about error recovery, a different concern. A dedicated `src/maintenance/` package keeps the responsibility isolated and gives a natural home for future cleanup-style features.

`JobArchiver` takes the `root_dir` and the configured `rejected_after_days`, and exposes a single `run() -> int` (returns count archived) method that:
- Loads `applications.json` via `ApplicationStore`.
- Loads `applications_archive.json` directly (simple list-append; archive file doesn't need migration logic since archived jobs are never re-read by the running app).
- Partitions jobs: `state in {"rejected", "archived"}` AND age (`now - parsed(archived_at or vetted_at or updated_at)`) `> rejected_after_days` → move to archive; everything else stays.
- Writes both files only if anything moved (avoids unnecessary disk writes / empty archive file creation).

**3. Timestamp fallback: `archived_at` first, then `vetted_at`, then `updated_at`.**
Each rejection path stamps its own precise timestamp at the moment of rejection (`archived_at` for score-based auto-reject, `vetted_at` for location hard-block) — these are the most accurate "age since rejection" signal and are checked first. Some legacy/migrated jobs may lack both, so `updated_at` is the final fallback. If none is present, the job is treated as "not old enough" (skipped, not archived) — safer default than guessing.

**4. Archive file format mirrors `applications.json` (flat JSON list), no dedup/migration on read.**
Keeps the implementation trivial — `json.load`/`json.dump` of a list, appending newly archived jobs to whatever's already there. No need to reuse `ApplicationStore`'s dedup-by-id-and-migration logic since the archive is write-mostly and not read by the running app.

**5. Wired into `_run_sync` as Step 4/4, after evaluate, swallowing failure into a warning (not aborting sync).**
Archival is housekeeping, not core pipeline functionality — if it fails, scout/enrich/evaluate results shouldn't be discarded. `_run_sync` will catch exceptions from `JobArchiver.run()` and print a warning rather than re-raising.

## Risks / Trade-offs

- **[Risk] Wrong age threshold archives jobs the user still wanted to see.** → Mitigation: default is a conservative 30 days, fully configurable, and archival (not deletion) means the data isn't actually lost.
- **[Risk] Archive file grows unboundedly over time, just like the problem we're solving.** → Mitigation: out of scope for this change (explicitly a non-goal to manage archive growth); acceptable since it's no longer loaded on every API/dashboard request, which was the actual pain point. Could be revisited later (e.g. periodic archive rotation).
- **[Risk] Running archival inside `sync` means it never runs if the user only runs `scout`/`enrich`/`evaluate` individually.** → Mitigation: acceptable per the user's explicit choice to hook into `sync` rather than add a new command; `sync` is described as "the full pipeline" and is the primary recommended entrypoint.

## Migration Plan

No data migration needed — this only adds a new optional step and a new file. First run after deploy will archive any currently-old rejected jobs; existing `applications.json` structure is untouched for non-archived jobs.

## Open Questions

None — scope was clarified with the user before this design was written (archive not delete, configurable threshold, runs inside `sync`).
