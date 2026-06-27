"""JobArchiver — moves old rejected jobs out of the active application store."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core.store import ApplicationStore

_REJECTED_STATE = "rejected"


class JobArchiver:
    def __init__(self, root_dir: Path, rejected_after_days: int) -> None:
        self._root = root_dir
        self._rejected_after_days = rejected_after_days
        self._store = ApplicationStore(root_dir / "artifacts" / "applications.json")
        self._archive_path = root_dir / "artifacts" / "applications_archive.json"

    def run(self) -> int:
        jobs = self._store.load()
        keep: list[dict] = []
        archive: list[dict] = []

        for job in jobs:
            if self._should_archive(job):
                archive.append(job)
            else:
                keep.append(job)

        if not archive:
            return 0

        self._store.save(keep)
        self._append_to_archive(archive)
        return len(archive)

    def _should_archive(self, job: dict) -> bool:
        if job.get("state") != _REJECTED_STATE:
            return False
        age_days = self._age_in_days(job)
        if age_days is None:
            return False
        return age_days > self._rejected_after_days

    @staticmethod
    def _age_in_days(job: dict) -> float | None:
        timestamp = job.get("vetted_at") or job.get("updated_at")
        if not timestamp:
            return None
        try:
            parsed = datetime.fromisoformat(timestamp)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - parsed
        return delta.total_seconds() / 86400

    def _append_to_archive(self, archive: list[dict]) -> None:
        existing: list[dict] = []
        if self._archive_path.exists():
            with self._archive_path.open() as f:
                existing = json.load(f)
        with self._archive_path.open("w") as f:
            json.dump(existing + archive, f, indent=2)
