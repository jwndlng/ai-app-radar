from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from core.config import AppConfigLoader, SettingsLocation


def test_archival_default_threshold(tmp_path: Path) -> None:
    (tmp_path / "configs").mkdir()
    settings = AppConfigLoader(tmp_path).settings()
    assert settings.archival.rejected_after_days == 30


def test_archival_custom_threshold(tmp_path: Path) -> None:
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "settings.yaml").write_text(
        yaml.safe_dump({"archival": {"rejected_after_days": 60}})
    )
    settings = AppConfigLoader(tmp_path).settings()
    assert settings.archival.rejected_after_days == 60


class TestSettingsLocation:
    def test_default_path_when_env_unset(self, tmp_path: Path) -> None:
        location = SettingsLocation(tmp_path, environ={})
        assert location.write_path == tmp_path / "configs" / "settings.yaml"
        assert location.read_path == tmp_path / "configs" / "settings.yaml"
        assert not location.is_overridden

    def test_blank_env_var_is_ignored(self, tmp_path: Path) -> None:
        location = SettingsLocation(tmp_path, environ={"RADAR_SETTINGS_PATH": "  "})
        assert location.write_path == tmp_path / "configs" / "settings.yaml"

    def test_absolute_override(self, tmp_path: Path) -> None:
        target = tmp_path / "data" / "settings.yaml"
        location = SettingsLocation(tmp_path, environ={"RADAR_SETTINGS_PATH": str(target)})
        assert location.write_path == target
        assert location.is_overridden

    def test_relative_override_resolves_against_root(self, tmp_path: Path) -> None:
        env = {"RADAR_SETTINGS_PATH": "artifacts/settings.yaml"}
        location = SettingsLocation(tmp_path, environ=env)
        assert location.write_path == tmp_path / "artifacts" / "settings.yaml"

    def test_missing_override_falls_back_to_bundled(self, tmp_path: Path) -> None:
        (tmp_path / "configs").mkdir()
        (tmp_path / "configs" / "settings.yaml").write_text("scout:\n  max_pages: 7\n")
        env = {"RADAR_SETTINGS_PATH": "artifacts/settings.yaml"}
        location = SettingsLocation(tmp_path, environ=env)
        assert location.read_path == tmp_path / "configs" / "settings.yaml"
        assert location.load() == {"scout": {"max_pages": 7}}

    def test_existing_override_is_sole_source(self, tmp_path: Path) -> None:
        (tmp_path / "configs").mkdir()
        (tmp_path / "configs" / "settings.yaml").write_text("scout:\n  max_pages: 7\n")
        (tmp_path / "artifacts").mkdir()
        (tmp_path / "artifacts" / "settings.yaml").write_text("enrich:\n  concurrency: 3\n")
        env = {"RADAR_SETTINGS_PATH": "artifacts/settings.yaml"}
        assert SettingsLocation(tmp_path, environ=env).load() == {"enrich": {"concurrency": 3}}

    def test_load_returns_empty_when_nothing_exists(self, tmp_path: Path) -> None:
        assert SettingsLocation(tmp_path, environ={}).load() == {}

    def test_writable_for_missing_file_in_missing_dir(self, tmp_path: Path) -> None:
        env = {"RADAR_SETTINGS_PATH": str(tmp_path / "a" / "b" / "settings.yaml")}
        assert SettingsLocation(tmp_path, environ=env).writable

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses permission bits")
    def test_not_writable_in_read_only_dir(self, tmp_path: Path) -> None:
        configs = tmp_path / "configs"
        configs.mkdir()
        (configs / "settings.yaml").write_text("scout: {}\n")
        (configs / "settings.yaml").chmod(0o444)
        configs.chmod(0o555)
        try:
            assert not SettingsLocation(tmp_path, environ={}).writable
        finally:
            configs.chmod(0o755)


def test_loader_reads_settings_from_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "settings.yaml").write_text("scout:\n  max_pages: 10\n")
    override = tmp_path / "data" / "settings.yaml"
    override.parent.mkdir()
    override.write_text(yaml.safe_dump({
        "scout": {"max_pages": 15},
        "notifications": {"telegram": {"bot_token": "from-override", "chat_id": "7"}},
    }))
    monkeypatch.setenv("RADAR_SETTINGS_PATH", str(override))
    loader = AppConfigLoader(tmp_path)
    assert loader.scout().max_pages == 15
    assert loader.notifications().bot_token == "from-override"
    assert loader.notifications().chat_id == "7"
