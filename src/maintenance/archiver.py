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
    def __init__(
        self,
        root_dir: Path,
        rejected_after_days: int,
        failed_after_days: int | None = None,
    ) -> None:
        self._root = root_dir
        self._rejected_after_days = rejected_after_days
        self._failed_after_days = failed_after_days
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

        # Write the archive file first, then delete from the store: the reverse
        # order loses the jobs permanently if the archive write fails.
        self._append_to_archive(archive)

        for job in archive:
            jid = job.get("id")
            if jid:
                self._store.delete_job(jid)

        return len(archive)

    def _should_archive(self, job: dict) -> bool:
        if job.get("state") in _ARCHIVABLE_STATES:
            age_days = self._age_in_days(job)
            return age_days is not None and age_days > self._rejected_after_days
        # Permanently failed jobs (dead listings, repeated fetch errors) are
        # cleaned up on their own, longer threshold — aged from the failure
        # time, so a fresh failure on an old job is not archived prematurely.
        if self._failed_after_days is not None and job.get("status") == "failed":
            age_days = self._age_in_days(job, prefer="failed_at")
            return age_days is not None and age_days > self._failed_after_days
        return False

    @staticmethod
    def _age_in_days(job: dict, prefer: str | None = None) -> float | None:
        timestamp = (
            (job.get(prefer) if prefer else None)
            or job.get("archived_at") or job.get("vetted_at") or job.get("updated_at")
        )
        if not timestamp:
            return None
        try:
            parsed = datetime.fromisoformat(timestamp)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            # Pipeline timestamps are naive local time; astimezone() on a
            # naive datetime attaches the local timezone.
            parsed = parsed.astimezone()
        delta = datetime.now(timezone.utc) - parsed
        return delta.total_seconds() / 86400

    def _append_to_archive(self, archive: list[dict]) -> None:
        existing: list[dict] = []
        if self._archive_path.exists():
            try:
                with self._archive_path.open() as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                # Preserve the unreadable archive instead of overwriting it.
                corrupt_path = self._archive_path.with_suffix(".json.corrupt")
                self._archive_path.replace(corrupt_path)
                existing = []
        # Write to a temp file and rename so a crash mid-write cannot
        # truncate the existing archive.
        tmp_path = self._archive_path.with_suffix(".json.tmp")
        with tmp_path.open("w") as f:
            json.dump(existing + archive, f, indent=2)
        tmp_path.replace(self._archive_path)
