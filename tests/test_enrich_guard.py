"""Tests for enrich placeholder guarding and scout title self-healing."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.config import ScoutConfig
from core.logger import RunLogger
from core.store import ApplicationStore
from enrich.consumer import _is_placeholder
from scout.consumer import ScoutConsumer


@pytest.mark.parametrize("value,expected", [
    ("", True),
    (None, True),
    ("<UNKNOWN>", True),
    ("Unknown", True),
    ("n/a", True),
    ("Multiple Open Roles at Anthropic", True),
    ("Multiple Open Roles (AI Research & Engineering)", True),
    ("Security Engineer", False),
    ("Zurich", False),
])
def test_is_placeholder(value, expected) -> None:
    assert _is_placeholder(value) is expected


def test_scout_restores_placeholder_title(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    store = ApplicationStore(artifacts / "radar.db")
    store.save_job({
        "id": "anthropic-securityengineer",
        "company": "Anthropic",
        "title": "<UNKNOWN>",
        "url": "https://example.com/j/1",
        "state": "review",
        "status": "ok",
    })

    consumer = ScoutConsumer(ScoutConfig(), tmp_path, RunLogger("scout", tmp_path))
    consumer._process_discovered(
        [{"company": "Anthropic", "title": "Security Engineer", "url": "https://example.com/j/1"}],
        "Anthropic", is_direct=True,
    )
    consumer._ingest()

    job = store.get_by_id("anthropic-securityengineer")
    assert job["title"] == "Security Engineer"
