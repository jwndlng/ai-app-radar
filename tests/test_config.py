from __future__ import annotations

from pathlib import Path

import yaml

from core.config import AppConfigLoader


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
