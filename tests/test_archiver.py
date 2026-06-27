from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from maintenance.archiver import JobArchiver


def _iso(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _write_jobs(tmp_path: Path, jobs: list[dict]) -> Path:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(exist_ok=True)
    apps_path = artifacts / "applications.json"
    apps_path.write_text(json.dumps(jobs))
    return apps_path


def test_old_rejected_job_is_archived(tmp_path: Path) -> None:
    jobs = [{"id": "1", "state": "rejected", "vetted_at": _iso(40)}]
    apps_path = _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 1
    assert json.loads(apps_path.read_text()) == []
    archive_path = tmp_path / "artifacts" / "applications_archive.json"
    archived = json.loads(archive_path.read_text())
    assert len(archived) == 1
    assert archived[0]["id"] == "1"


def test_recent_rejected_job_is_not_archived(tmp_path: Path) -> None:
    jobs = [{"id": "1", "state": "rejected", "vetted_at": _iso(5)}]
    apps_path = _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 0
    assert json.loads(apps_path.read_text()) == jobs
    assert not (tmp_path / "artifacts" / "applications_archive.json").exists()


def test_non_rejected_jobs_are_never_archived(tmp_path: Path) -> None:
    jobs = [
        {"id": "1", "state": "match", "vetted_at": _iso(400)},
        {"id": "2", "state": "applied", "vetted_at": _iso(400)},
        {"id": "3", "state": "archived", "vetted_at": _iso(400)},
    ]
    apps_path = _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 0
    assert json.loads(apps_path.read_text()) == jobs


def test_rejected_job_missing_timestamps_left_in_place(tmp_path: Path) -> None:
    jobs = [{"id": "1", "state": "rejected"}]
    apps_path = _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 0
    assert json.loads(apps_path.read_text()) == jobs


def test_fallback_to_updated_at_when_vetted_at_absent(tmp_path: Path) -> None:
    jobs = [{"id": "1", "state": "rejected", "updated_at": _iso(40)}]
    apps_path = _write_jobs(tmp_path, jobs)
    archived_count = JobArchiver(tmp_path, rejected_after_days=30).run()

    assert archived_count == 1
    assert json.loads(apps_path.read_text()) == []


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
