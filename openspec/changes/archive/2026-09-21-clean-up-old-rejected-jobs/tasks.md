## 1. Config

- [x] 1.1 Add `ArchivalSettings` dataclass (`rejected_after_days: int = 30`) to `src/core/config.py`
- [x] 1.2 Add `archival: ArchivalSettings` field to `AppSettings`
- [x] 1.3 Load the `archival:` section from `configs/settings.yaml` in `AppConfigLoader.settings()`
- [x] 1.4 Document the new `archival.rejected_after_days` key in `configs/settings.yaml` (with default commented or set)

## 2. JobArchiver

- [x] 2.1 Create `src/maintenance/` package (`__init__.py`)
- [x] 2.2 Implement `JobArchiver` class in `src/maintenance/archiver.py`: constructor takes `root_dir: Path` and `rejected_after_days: int`
- [x] 2.3 Implement age calculation helper: parse `vetted_at` (fallback `updated_at`); skip (treat as not-old-enough) if neither is present
- [x] 2.4 Implement `run() -> int`: load `applications.json` via `ApplicationStore`, partition jobs into keep/archive sets per the spec rules, load+append+save `applications_archive.json` as a plain JSON list, save `applications.json` only if anything was removed, return count archived
- [x] 2.5 Ensure `run()` is a no-op (no writes) when no job qualifies

## 3. Wire into sync

- [x] 3.1 In `src/cli.py::_run_sync`, after the evaluate step, construct `JobArchiver` from `loader.settings().archival.rejected_after_days` and call `run()`
- [x] 3.2 Wrap the archival call in a try/except that prints a warning on failure without re-raising, so scout/enrich/evaluate results are preserved
- [x] 3.3 Print a short summary line (e.g. number of jobs archived) on success, consistent with existing `[sync] Step N/M` style logging

## 4. Tests

- [x] 4.1 Unit test: rejected job older than threshold (via `vetted_at`) is moved to archive file
- [x] 4.2 Unit test: rejected job within threshold stays in `applications.json`
- [x] 4.3 Unit test: non-rejected job (e.g. `match`, `applied`, `archived` state) is never archived regardless of age
- [x] 4.4 Unit test: rejected job missing both `vetted_at` and `updated_at` is left in place
- [x] 4.5 Unit test: fallback to `updated_at` when `vetted_at` is absent
- [x] 4.6 Unit test: archiving appends to an existing `applications_archive.json` rather than overwriting it
- [x] 4.7 Unit test: `run()` returns `0` and writes nothing when no job qualifies
- [x] 4.8 Unit test: `AppConfigLoader.settings().archival.rejected_after_days` defaults to `30` and respects a configured override
- [x] 4.9 Integration test: `_run_sync` invokes `JobArchiver.run()` once, after evaluate, and a raised exception is caught and logged as a warning without failing sync
