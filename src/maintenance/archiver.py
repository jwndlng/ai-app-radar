"""JobArchiver — moves old rejected jobs out of the active application store."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core.store import ApplicationStore

# "rejected" = location hard-block (EvaluateConsumer._reject_job, stamps vetted_at).
# "archived" = score-based auto-reject (EvaluateConsumer._archive_job, stamps archived_at).
# Both are terminal, no-future-value outcomes and are candidates for archival.
_ARCHIVABLE_STATES = frozenset({"rejected", "archived"})


class JobArchiver:
    def __init__(self, root_dir: Path, rejected_after_days: int) -> None:
        self._root = root_dir
        self._rejected_after_days = rejected_after_days
        self._store = ApplicationStore(root_dir / "artifacts" / "radar.db")
        self._archive_path = root_dir / "artifacts" / "applications_archive.json"

    def run(self) -> int:
        jobs = self._store.load()
        archive: list[dict] = []

        for job in jobs:
            if self._should_archive(job):
                archive.append(job)

        if not archive:
            return 0

        for job in archive:
            jid = job.get("id")
            if jid:
                self._store.delete_job(jid)

        self._append_to_archive(archive)
        return len(archive)

    def _should_archive(self, job: dict) -> bool:
        if job.get("state") not in _ARCHIVABLE_STATES:
            return False
        age_days = self._age_in_days(job)
        if age_days is None:
            return False
        return age_days > self._rejected_after_days

    @staticmethod
    def _age_in_days(job: dict) -> float | None:
        timestamp = job.get("archived_at") or job.get("vetted_at") or job.get("updated_at")
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
