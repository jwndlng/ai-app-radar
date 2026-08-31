from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.store import ApplicationStore
from maintenance.archiver import JobArchiver


def _iso(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _write_jobs(tmp_path: Path, jobs: list[dict]) -> ApplicationStore:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(exist_ok=True)
    store = ApplicationStore(artifacts / "radar.db")
    store.save(jobs)
    return store


def test_old_rejected_job_is_archived(tmp_path: Path) -> None:
    jobs = [{"id": "1", "state": "rejected", "vetted_at": _iso(40)}]
    store = _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 1
    assert store.load() == []
    archive_path = tmp_path / "artifacts" / "applications_archive.json"
    archived = json.loads(archive_path.read_text())
    assert len(archived) == 1
    assert archived[0]["id"] == "1"


def test_recent_rejected_job_is_not_archived(tmp_path: Path) -> None:
    jobs = [{"id": "1", "state": "rejected", "vetted_at": _iso(5)}]
    store = _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 0
    assert len(store.load()) == 1
    assert not (tmp_path / "artifacts" / "applications_archive.json").exists()


def test_non_terminal_jobs_are_never_archived(tmp_path: Path) -> None:
    jobs = [
        {"id": "1", "state": "match", "vetted_at": _iso(400)},
        {"id": "2", "state": "applied", "vetted_at": _iso(400)},
        {"id": "3", "state": "review", "vetted_at": _iso(400)},
    ]
    store = _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 0
    assert len(store.load()) == 3


def test_old_auto_rejected_job_is_archived(tmp_path: Path) -> None:
    jobs = [{"id": "1", "state": "archived", "archived_at": _iso(40)}]
    store = _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 1
    assert store.load() == []
    archive_path = tmp_path / "artifacts" / "applications_archive.json"
    archived = json.loads(archive_path.read_text())
    assert archived[0]["id"] == "1"


def test_recent_auto_rejected_job_is_not_archived(tmp_path: Path) -> None:
    jobs = [{"id": "1", "state": "archived", "archived_at": _iso(5)}]
    store = _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 0
    assert len(store.load()) == 1


def test_rejected_job_missing_timestamps_left_in_place(tmp_path: Path) -> None:
    jobs = [{"id": "1", "state": "rejected"}]
    store = _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 0
    assert len(store.load()) == 1


def test_fallback_to_updated_at_when_vetted_at_absent(tmp_path: Path) -> None:
    jobs = [{"id": "1", "state": "rejected", "updated_at": _iso(40)}]
    store = _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 1
    assert store.load() == []


def test_archive_accumulates_across_runs(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(exist_ok=True)
    archive_path = artifacts / "applications_archive.json"
    archive_path.write_text(json.dumps([{"id": "old", "state": "rejected"}]))

    jobs = [{"id": "new", "state": "rejected", "vetted_at": _iso(40)}]
    _write_jobs(tmp_path, jobs)
    JobArchiver(tmp_path, rejected_after_days=30).run()

    archived = json.loads(archive_path.read_text())
    assert {j["id"] for j in archived} == {"old", "new"}


def test_run_returns_zero_and_writes_nothing_when_nothing_qualifies(tmp_path: Path) -> None:
    jobs = [{"id": "1", "state": "rejected", "vetted_at": _iso(5)}]
    _write_jobs(tmp_path, jobs)
    archive_path = tmp_path / "artifacts" / "applications_archive.json"

    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 0
    assert not archive_path.exists()


def test_corrupt_archive_is_preserved_and_jobs_not_lost(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(exist_ok=True)
    archive_path = artifacts / "applications_archive.json"
    archive_path.write_text("{not valid json")

    jobs = [{"id": "1", "state": "rejected", "vetted_at": _iso(40)}]
    _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 1
    # The archived job landed in a fresh archive file …
    archived = json.loads(archive_path.read_text())
    assert [j["id"] for j in archived] == ["1"]
    # … and the corrupt original was moved aside, not overwritten.
    assert (artifacts / "applications_archive.json.corrupt").read_text() == "{not valid json"


def test_manual_rejection_age_counts_from_rejection_not_evaluation(tmp_path: Path) -> None:
    # A job evaluated 40 days ago (stale vetted_at) but manually rejected
    # 5 days ago (fresh vetted_at, as stamped by the API route) must not be
    # archived yet with a 30-day threshold.
    jobs = [{"id": "1", "state": "rejected", "vetted_at": _iso(5), "updated_at": _iso(5)}]
    store = _write_jobs(tmp_path, jobs)
    assert JobArchiver(tmp_path, rejected_after_days=30).run() == 0
    assert len(store.load()) == 1
