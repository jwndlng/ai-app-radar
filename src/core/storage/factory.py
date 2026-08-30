"""Storage factory for creating database providers."""

from __future__ import annotations

from pathlib import Path

from core.storage.base import DatabaseProvider
from core.storage.sqlite import SQLiteStorageProvider


class StorageFactory:
    """Factory responsible for instantiating concrete DatabaseProvider implementations."""

    @classmethod
    def create_provider(
        cls,
        root_dir: Path | str,
        provider_type: str = "sqlite",
        db_path: Path | str | None = None,
        connection_url: str | None = None,
    ) -> DatabaseProvider:
        """Create a DatabaseProvider instance based on provider_type configuration."""
        norm_type = (provider_type or "sqlite").lower().strip()

        if norm_type == "sqlite":
            target_path = Path(db_path) if db_path else Path(root_dir) / "artifacts" / "radar.db"
            return SQLiteStorageProvider(target_path)

        if norm_type in ("postgres", "postgresql"):
            # PostgreSQL hook: can be configured with connection_url when adding psycopg2/asyncpg
            raise NotImplementedError(
                "PostgreSQL provider hook is reserved for multi-user deployments. "
                "Configure 'sqlite' for embedded single-node storage."
            )

        raise ValueError(f"Unknown database provider type: {provider_type}")

