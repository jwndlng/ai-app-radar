# Proposal

## Why

On the self-hosted deployment (k8s/NAS behind a reverse proxy), saving settings in the UI fails with
"Saving settings failed — changes are NOT persisted" and `PUT /api/settings` returns 500. The same
code round-trips correctly when run locally, so the failure is environmental: the server cannot
write `configs/settings.yaml` (typically a read-only mount such as a ConfigMap, or a directory
owned by a different UID). Today there is no way to point settings at a writable location, the
backend swallows the underlying `OSError` without logging it, and the UI discards the error body —
so the user gets no hint of the cause and no way to fix it.

## What Changes

- Make the settings file location configurable via a `RADAR_SETTINGS_PATH` environment variable
  (default stays `configs/settings.yaml`). Reads and writes both use the resolved path, so a
  deployment can keep `/app/configs` read-only and persist settings on a writable volume
  (e.g. `/app/artifacts/settings.yaml`).
- When `RADAR_SETTINGS_PATH` points to a file that doesn't exist yet, read the bundled
  `configs/settings.yaml` as the base so existing values (including `notifications`) carry over on
  first save. The parent directory is created on save if missing.
- `PUT /api/settings` returns a descriptive error (`{"ok": false, "error": "...", "path": "..."}`)
  naming the target path and OS error when the write fails, and logs the failure server-side.
- `GET /api/settings` additionally returns a `meta` object `{path, writable}` so the UI can warn
  up front when settings cannot be persisted.
- The Settings view shows the server's error message on save failure and a persistent warning
  banner (with the path and a hint about `RADAR_SETTINGS_PATH`) when settings are not writable.
- Document `RADAR_SETTINGS_PATH` in the README and pass it through in `docker-compose.yml`.

Non-goals: the same read-only problem can affect `PUT /api/profile` (`configs/profile.yaml` and
`configs/backups/`); that is left for a follow-up change.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `app-settings`: settings file location becomes configurable via `RADAR_SETTINGS_PATH`, with
  fallback to the bundled file as the base when the override file doesn't exist yet.
- `webapp-api`: `GET /api/settings` exposes `meta.path`/`meta.writable`; `PUT /api/settings`
  writes to the resolved path and returns a descriptive error on write failure.
- `ui`: Settings view surfaces the server's save error and warns when settings are
  read-only.

## Impact

- `src/core/config.py` — new `SettingsLocation` class resolving the read/write paths;
  `AppConfigLoader.settings()` / `notifications()` read through it.
- `src/api/deps.py` — `PipelineRunner.load_settings()` / `save_settings()` use the resolved path,
  report writability, create parent dirs.
- `src/api/routes.py` — settings PUT handles `OSError` with a descriptive 500 and logs it.
- `static/index.html` — `saveSettings()` error text, read-only banner in the Settings view.
- `docker-compose.yml`, `README.md` — new env var documented.
- Tests under `tests/` for path resolution, fallback seeding, and write-failure responses.
- No new dependencies; no breaking changes (default path unchanged).
