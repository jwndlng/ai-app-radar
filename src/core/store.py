"""ApplicationStore — persistence layer delegating to pluggable database storage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.storage.base import DatabaseProvider
from core.storage.migration import LegacyJsonMigrator
from core.storage.repository import JobRepository
from core.storage.sqlite import SQLiteStorageProvider

_STATE_MIGRATION: dict[str, tuple[str, str]] = {
    "new": ("discovered", "ok"),
    "enriched": ("parsed", "ok"),
    "in_progress": ("match", "ok"),
    "review": ("review", "ok"),
    "archived": ("archived", "ok"),
    "applied": ("applied", "ok"),
}


class ApplicationStore:
    """Persistence store wrapping JobRepository and SQLiteStorageProvider."""

    def __init__(self, path: Path | str, provider: DatabaseProvider | None = None) -> None:
        self._path = Path(path) if isinstance(path, str) and path != ":memory:" else path

        if provider is not None:
            self._provider = provider
        else:
            if str(path) == ":memory:":
                db_path = ":memory:"
                self._provider = SQLiteStorageProvider(db_path)
            else:
                p = Path(path)
                if p.suffix in (".db", ".sqlite"):
                    db_path = p
                    root_dir = p.parent.parent if p.parent.name == "artifacts" else p.parent
                else:
                    db_path = p.parent / "radar.db" if p.name.endswith(".json") else p / "radar.db"
                    root_dir = p.parent.parent if p.parent.name == "artifacts" else p.parent

                self._provider = SQLiteStorageProvider(db_path)
                LegacyJsonMigrator(root_dir).migrate_if_needed(self._provider)

        self._repo = JobRepository(self._provider)

    @property
    def repository(self) -> JobRepository:
        return self._repo

    @property
    def provider(self) -> DatabaseProvider:
        return self._provider

    def load(self) -> list[dict[str, Any]]:
        """Load all job records from storage."""
        return self._repo.load_all()

    def save(self, data: list[dict[str, Any]]) -> None:
        """Save/upsert a collection of job records."""
        self._repo.save_all(data)

    def save_job(self, job: dict[str, Any]) -> None:
        """Save/upsert a single job record."""
        self._repo.save(job)

    def get_by_id(self, job_id: str) -> dict[str, Any] | None:
        """Retrieve a single job by ID."""
        return self._repo.get(job_id)

    def get_by_url(self, url: str) -> dict[str, Any] | None:
        """Retrieve a single job by URL."""
        return self._repo.get_by_url(url)

    def delete_job(self, job_id: str) -> bool:
        """Delete a job by ID."""
        return self._repo.delete(job_id)

    def list_jobs(
        self,
        state: str | None = None,
        status: str | None = None,
        search: str | None = None,
        favorited_only: bool = False,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        projection: str = "summary",
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List jobs with optional filtering, search, sorting, and projection."""
        return self._repo.list_jobs(
            state=state,
            status=status,
            search=search,
            favorited_only=favorited_only,
            sort_by=sort_by,
            sort_order=sort_order,
            projection=projection,
            limit=limit,
            offset=offset,
        )

    def state_counts(self) -> dict[str, int]:
        """Return state count aggregations."""
        return self._repo.state_counts()

    @staticmethod
    def _migrate(job: dict) -> dict:
        """Translate legacy single-field status to state + status."""
        if "state" in job:
            return job
        old_status = job.pop("status", "new")
        if old_status == "failed":
            job["state"] = "discovered"
            job["status"] = "failed"
            err = job.pop("enrich_error", None)
            if err:
                job["error_message"] = err
        else:
            state, status = _STATE_MIGRATION.get(old_status, ("discovered", "ok"))
            job["state"] = state
            job["status"] = status
        return job
