"""Abstract base interface for pluggable database storage providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class DatabaseProvider(ABC):
    """Abstract interface defining required persistence operations for job records."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize database schema, tables, and indexes."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Close open connections and release resources."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, job_id: str) -> dict | None:
        """Fetch a single job by its unique primary ID."""
        raise NotImplementedError

    @abstractmethod
    def get_by_url(self, url: str) -> dict | None:
        """Fetch a single job by its posting URL."""
        raise NotImplementedError

    @abstractmethod
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
    ) -> list[dict]:
        """List job records with optional filtering, search, sorting, and projection."""
        raise NotImplementedError

    @abstractmethod
    def upsert(self, job: dict) -> None:
        """Insert or update a single job record atomically."""
        raise NotImplementedError

    @abstractmethod
    def upsert_batch(self, jobs: list[dict]) -> None:
        """Insert or update a batch of job records in a single transaction."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, job_id: str) -> bool:
        """Delete a job record by ID. Returns True if found and deleted, False otherwise."""
        raise NotImplementedError

    @abstractmethod
    def get_state_counts(self) -> dict[str, int]:
        """Return counts of jobs grouped by state and status."""
        raise NotImplementedError

    @abstractmethod
    def count_all(self) -> int:
        """Return total number of stored jobs."""
        raise NotImplementedError
