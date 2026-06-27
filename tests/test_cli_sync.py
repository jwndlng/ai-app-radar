from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from cli import PipelineCLI


@pytest.mark.asyncio
async def test_sync_invokes_archival_once_after_evaluate(tmp_path: Path, monkeypatch) -> None:
    cli = PipelineCLI(tmp_path)
    cli._run_scout = AsyncMock()
    cli._run_enrich = AsyncMock()
    cli._run_evaluate = AsyncMock()

    calls: list[str] = []
    monkeypatch.setattr(cli, "_run_archival", lambda: calls.append("archival"))

    await cli._run_sync()

    assert calls == ["archival"]
    cli._run_scout.assert_awaited_once()
    cli._run_enrich.assert_awaited_once()
    cli._run_evaluate.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_survives_archival_failure(tmp_path: Path, monkeypatch) -> None:
    """_run_archival itself swallows archiver errors, so sync completes normally."""
    cli = PipelineCLI(tmp_path)
    cli._run_scout = AsyncMock()
    cli._run_enrich = AsyncMock()
    cli._run_evaluate = AsyncMock()

    class _BoomArchiver:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def run(self) -> int:
            raise RuntimeError("archival exploded")

    monkeypatch.setattr("maintenance.archiver.JobArchiver", _BoomArchiver)

    await cli._run_sync()  # must not raise

    cli._run_scout.assert_awaited_once()
    cli._run_enrich.assert_awaited_once()
    cli._run_evaluate.assert_awaited_once()


def test_run_archival_catches_exceptions(tmp_path: Path, monkeypatch, capsys) -> None:
    cli = PipelineCLI(tmp_path)

    class _BoomArchiver:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def run(self) -> int:
            raise RuntimeError("disk full")

    monkeypatch.setattr("maintenance.archiver.JobArchiver", _BoomArchiver)

    cli._run_archival()

    captured = capsys.readouterr()
    assert "Warning: archival step failed" in captured.out
