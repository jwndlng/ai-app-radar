from __future__ import annotations

import json
from pathlib import Path

import pytest

from scout.state_tracker import StateTracker


def _make_tracker(tmp_path: Path, jobs: list[dict]) -> StateTracker:
    """Write jobs to artifacts/applications.json and return a loaded StateTracker."""
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "applications.json").write_text(json.dumps(jobs))
    return StateTracker(tmp_path)


def test_generate_id_is_stable(tmp_path: Path) -> None:
    tracker = StateTracker(tmp_path)
    assert tracker.generate_id("Acme Corp", "Senior Engineer") == "acmecorp-seniorengineer"
    # Calling twice produces the same value
    assert tracker.generate_id("Acme Corp", "Senior Engineer") == tracker.generate_id("Acme Corp", "Senior Engineer")


def test_generate_id_normalises_case_and_punctuation(tmp_path: Path) -> None:
    tracker = StateTracker(tmp_path)
    assert tracker.generate_id("ACME", "Senior Engineer") == tracker.generate_id("acme", "senior engineer")


def test_get_existing_by_url_hit(tmp_path: Path) -> None:
    jobs = [{"company": "Stripe", "title": "SWE", "url": "https://stripe.com/j/1"}]
    tracker = _make_tracker(tmp_path, jobs)
    result = tracker.get_existing_by_url("https://stripe.com/j/1")
    assert result is not None
    assert result["company"] == "Stripe"


def test_get_existing_by_url_miss(tmp_path: Path) -> None:
    tracker = _make_tracker(tmp_path, [])
    assert tracker.get_existing_by_url("https://unknown.com/job") is None


def test_get_existing_job_hit(tmp_path: Path) -> None:
    jobs = [{"company": "Stripe", "title": "Security Engineer", "url": "https://stripe.com/j/1"}]
    tracker = _make_tracker(tmp_path, jobs)
    assert tracker.get_existing_job("Stripe", "Security Engineer") is not None


def test_get_existing_job_miss(tmp_path: Path) -> None:
    tracker = _make_tracker(tmp_path, [])
    assert tracker.get_existing_job("Stripe", "Security Engineer") is None


def test_empty_state_no_file(tmp_path: Path) -> None:
    """StateTracker should initialise cleanly when no applications.json exists."""
    tracker = StateTracker(tmp_path)
    assert tracker.get_existing_by_url("https://anything.com") is None
    assert tracker.get_existing_job("Acme", "SWE") is None


def test_deduplication_by_url(tmp_path: Path) -> None:
    jobs = [
        {"company": "Stripe", "title": "SWE", "url": "https://stripe.com/j/1"},
        {"company": "Stripe", "title": "SWE2", "url": "https://stripe.com/j/2"},
    ]
    tracker = _make_tracker(tmp_path, jobs)
    assert tracker.get_existing_by_url("https://stripe.com/j/1") is not None
    assert tracker.get_existing_by_url("https://stripe.com/j/2") is not None
    assert tracker.get_existing_by_url("https://stripe.com/j/3") is None
