"""Domain-level repository wrapping database storage providers."""

from __future__ import annotations

from typing import Any

from core.storage.base import DatabaseProvider


class JobRepository:
    """High-level repository for application job records."""

    def __init__(self, provider: DatabaseProvider) -> None:
        self._provider = provider

    @property
    def provider(self) -> DatabaseProvider:
        return self._provider

    def get(self, job_id: str) -> dict[str, Any] | None:
        return self._provider.get_by_id(job_id)

    def get_by_url(self, url: str) -> dict[str, Any] | None:
        return self._provider.get_by_url(url)

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
        return self._provider.list_jobs(
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

    def load_all(self, projection: str = "full") -> list[dict[str, Any]]:
        return self._provider.list_jobs(projection=projection)

    def save(self, job: dict[str, Any]) -> None:
        self._provider.upsert(job)

    def save_batch(self, jobs: list[dict[str, Any]]) -> None:
        self._provider.upsert_batch(jobs)

    def save_all(self, jobs: list[dict[str, Any]]) -> None:
        self._provider.upsert_batch(jobs)

    def delete(self, job_id: str) -> bool:
        return self._provider.delete(job_id)

    def state_counts(self) -> dict[str, int]:
        return self._provider.get_state_counts()

    def count(self) -> int:
        return self._provider.count_all()
