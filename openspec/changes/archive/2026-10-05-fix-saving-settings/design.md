# Design

## Context

See proposal.md — Why. Current state relevant to the approach:

- The path `configs/settings.yaml` is hardcoded in three places: `AppConfigLoader.settings()` and
  `AppConfigLoader.notifications()` (`src/core/config.py`, both via `_yaml("configs/settings.yaml")`)
  and `PipelineRunner._settings_path()` (`src/api/deps.py`).
- `PipelineRunner.save_settings()` reads the existing YAML, overlays the editable sections, and
  writes with `path.write_text(...)`. Any `OSError` propagates to the route, which catches
  `Exception` and returns `{"ok": false, "error": str(e)}` with 500 — but nothing is logged.
- `saveSettings()` in `static/index.html` throws `new Error('HTTP ' + r.status)` without reading
  the body and shows a fixed message, so the `error` field is never seen.
- Reproduced locally: GET → PUT round-trip returns 200. The user's deployment (k8s/NAS behind a
  reverse proxy) returns 500, consistent with an unwritable `/app/configs`. The image runs as
  root, so a read-only mount (ConfigMap or `:ro` volume) or a `runAsUser`/non-root setup is the
  most plausible cause.
- The Dockerfile already declares `/app/artifacts` as a volume, and it must be writable for the
  app to work at all (SQLite DB, `tasks.json`), so it's a natural home for persisted settings.

## Goals / Non-Goals

**Goals:**
- One resolution point for the settings path, shared by readers and the writer.
- Zero behavior change for deployments that don't set `RADAR_SETTINGS_PATH`.
- A read-only deployment shows an actionable message *before* the user edits anything.

**Non-Goals:**
- Atomic write-via-rename. A k8s `subPath` single-file mount can't be replaced by rename (`EBUSY`),
  so the in-place write stays.
- Auto-detecting a writable fallback location. Silently writing somewhere else would make it
  unclear which file wins on the next restart.
- Profile persistence (`configs/profile.yaml`, `configs/backups/`) — follow-up change.

## Decisions

### 1. `SettingsLocation` class in `src/core/config.py`

A small class (per CLAUDE.md: no bare functions) built from `root_dir` and `os.environ`:

```python
class SettingsLocation:
    ENV_VAR = "RADAR_SETTINGS_PATH"
    DEFAULT_RELATIVE = Path("configs") / "settings.yaml"

    def __init__(self, root_dir: Path, environ: Mapping[str, str] | None = None) -> None: ...

    @property
    def write_path(self) -> Path:   # env override (relative → root) or default
    @property
    def read_path(self) -> Path:    # write_path if it exists, else bundled default
    @property
    def is_overridden(self) -> bool:
    @property
    def writable(self) -> bool:     # see decision 3
    def load(self) -> dict:         # yaml.safe_load(read_path) or {} when absent
```

`AppConfigLoader.settings()` and `notifications()` call `SettingsLocation(self._root).load()`
instead of `_yaml("configs/settings.yaml")`. `PipelineRunner` replaces `_settings_path()` with a
`SettingsLocation`, and `save_settings()` uses `load()` for the base dict (so the bundled file
seeds the first override write, keeping `notifications`) and `write_path` as the target.
`write_path.parent.mkdir(parents=True, exist_ok=True)` runs before writing.

`environ` is injectable for tests; production passes nothing and uses `os.environ`. The location
is resolved per call, not cached, matching how `AppConfigLoader` re-reads the file today.

*Alternative considered:* a generic `RADAR_CONFIG_DIR` moving all of `configs/`. Rejected:
`companies.json` and `profile.yaml` are often deliberately managed as read-only config, and
moving them changes more behavior than this bug needs.

### 2. Read fallback only when the override file is missing

If `RADAR_SETTINGS_PATH` exists it is the only source. No deep merge of bundled and override.
That keeps the rule simple: "the override file, once it exists, is the settings". The first save
copies the bundled content forward, so nothing is lost.

*Alternative considered:* always deep-merge override over bundled. Rejected: hard to reason
about (deleting a key in the override would silently resurrect the bundled value), and it
changes the existing "missing key → dataclass default" rule.

### 3. Writability check

`writable` is `os.access(write_path, os.W_OK)` when the file exists. Otherwise it walks up to the
nearest existing ancestor and checks `os.access(ancestor, os.W_OK | os.X_OK)`. `os.access`
honours read-only mounts (`EROFS`) on Linux. It's advisory only: the PUT still attempts the
write and reports the real error, so a wrong guess can't block a save.

### 4. Error contract

`PipelineRunner.save_settings()` lets `OSError` propagate. The route catches `OSError`
specifically, logs with `logger.exception` (new module logger in `routes.py`), and returns 500
`{"ok": false, "error": f"Cannot write settings to {path}: {e.strerror or e}", "path": str(path)}`.
Other exceptions keep the existing generic 500 handling. `load_settings()` adds
`"meta": {"path": str(write_path), "writable": bool}` to the `dataclasses.asdict(...)` result.
`save_settings()` only copies `_EDITABLE_SETTINGS_SECTIONS`, so a posted-back `meta` is ignored
for free.

### 5. Frontend

- `saveSettings()`: on `!r.ok`, try `await r.json()` and use `d.error`, else `'HTTP ' + r.status`.
  Show `'Saving settings failed — ' + reason`.
- `loadSettings()`: store `d.meta` in a new `settingsMeta` property (default
  `{ path: '', writable: true }`) rather than merging it into `settings`, then `delete d.meta`
  before the spread.
- Banner at the top of the settings view, `x-show="!settingsMeta.writable"`, using the existing
  warning colour tokens from the ui-color-system spec: "Settings can't be saved — `<path>` is not
  writable. Set `RADAR_SETTINGS_PATH` to a writable location (e.g. /app/artifacts/settings.yaml)."

### 6. Deployment docs

Add `RADAR_SETTINGS_PATH` to the `environment:` passthrough in `docker-compose.yml` and a
"Running with read-only configs (Kubernetes/NAS)" note in README next to the
`configs/settings.yaml` section.

## Risks / Trade-offs

- [The actual 500 has another cause, e.g. a YAML error in a hand-edited file] → The descriptive
  error and server log make that visible on the next attempt. Non-`OSError` failures still return
  500 with `str(e)`, which the UI now shows.
- [`os.access` is wrong under some ACL/NFS setups] → Advisory only. The save path reports the
  true error.
- [Users set the env var but forget to persist the volume, and settings reset on pod restart] →
  README recommends a path under the `/app/artifacts` volume, which must already be persistent.
- [Two sources of truth after first save: the bundled file is ignored once the override exists] →
  Intended, and documented. `meta.path` in the UI shows which file is live.

## Migration Plan

No data migration. Existing deployments are unaffected until they set `RADAR_SETTINGS_PATH`.
For the reported deployment: set `RADAR_SETTINGS_PATH=/app/artifacts/settings.yaml`, redeploy,
and save once from the UI. The current ConfigMap values seed the new file. Rollback: unset the
env var; the app reads `configs/settings.yaml` again.
