# Tasks

## 1. Settings path resolution (core)

- [x] 1.1 Add `SettingsLocation` to `src/core/config.py`. It needs `write_path` (`RADAR_SETTINGS_PATH`, relative paths resolved against root, else `configs/settings.yaml`), `read_path` (the override if it exists, else the bundled default), `is_overridden`, `writable` (`os.access` on the file, or on the nearest existing ancestor dir) and `load()`, with an injectable `environ`. Verify with new unit tests in `tests/test_config.py` for: default path, absolute and relative override, fallback read when the override file is missing, and `writable=False` on a `chmod 0o555` temp dir (skipped when running as root).
- [x] 1.2 Route `AppConfigLoader.settings()` and `AppConfigLoader.notifications()` through `SettingsLocation(self._root).load()`. Verify with a `tests/test_config.py` test: with `RADAR_SETTINGS_PATH` set via `monkeypatch.setenv` to a file holding `scout.max_pages: 15` and Telegram values, `scout().max_pages == 15` and `notifications()` returns the override's values. Existing config tests must still pass.

## 2. API

- [x] 2.1 In `src/api/deps.py`, replace `_settings_path()` with `SettingsLocation`. `save_settings()` loads its base from `load()` (so the bundled file seeds the first override write), creates `write_path.parent` if missing, and writes to `write_path`. `load_settings()` adds `meta: {path, writable}`. Verify in `tests/test_api_routes.py`: GET includes `meta.writable is True`, and the existing round-trip test still passes even though the payload now contains `meta`, with no `meta` key written to the YAML.
- [x] 2.2 Add a test in `tests/test_api_routes.py` for the override path. With `RADAR_SETTINGS_PATH` pointing to a missing file in a not-yet-existing subdirectory of `tmp_path`, a PUT creates it with the edited sections plus the bundled `notifications.telegram` block, and leaves `configs/settings.yaml` byte-identical.
- [x] 2.3 In `src/api/routes.py`, add a module `logger` and catch `OSError` in `PUT /api/settings`. It logs with `logger.exception` and returns 500 `{"ok": false, "error": "Cannot write settings to <path>: <strerror>", "path": "<path>"}`. Verify with a test that monkeypatches the write to raise `OSError(errno.EROFS, "Read-only file system")` (or uses a read-only dir) and asserts the status, `ok: false`, that the path and "Read-only file system" appear in `error`, and that `meta.writable` is `False` on GET in the read-only-dir variant.

## 3. Frontend

- [x] 3.1 In `static/index.html`, change `saveSettings()` so that on a non-2xx response it parses JSON when possible and shows `'Saving settings failed — ' + (d.error || 'HTTP ' + r.status)`. Verify manually: make the settings file read-only, click Save, and confirm the toast shows the path and OS error. With a non-JSON body the toast shows the HTTP status.
- [x] 3.2 Add a `settingsMeta` state (default `{ path: '', writable: true }`). Fill it in `loadSettings()` and strip `meta` before merging into `settings`. Add a warning banner at the top of the settings view (`x-show="!settingsMeta.writable"`) using the existing `--status-review-*` tokens, showing the path and the `RADAR_SETTINGS_PATH` hint. Verify manually in light and dark mode: the banner appears when the file is read-only and is hidden when it's writable, and the Save buttons stay enabled.

## 4. Docs & deployment

- [x] 4.1 Add `RADAR_SETTINGS_PATH` to the `environment:` passthrough in `docker-compose.yml`. Verify with `docker compose config` (or by reading the file) that the variable is listed.
- [x] 4.2 Add a "Read-only configs (Kubernetes / NAS)" note to `README.md` under the `configs/settings.yaml` section. It should explain `RADAR_SETTINGS_PATH`, recommend `/app/artifacts/settings.yaml`, and note that the bundled file seeds the first save. Verify that the README renders and mentions the variable.

## 5. Verification

- [x] 5.1 Run the full test suite (`uv run pytest`) and confirm it is green. Run `openspec validate fix-saving-settings --strict` and confirm it passes.
- [x] 5.2 End-to-end local check: start `python -m main serve` with `configs/` made read-only (`chmod 555`) and confirm the UI banner and the descriptive save error. Restart with `RADAR_SETTINGS_PATH=artifacts/settings.yaml`, save from the UI, and confirm the new file exists with the edits plus `notifications`, and that a reload shows the saved values. Restore the permissions afterwards.
