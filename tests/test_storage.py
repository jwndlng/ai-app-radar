"""Unit tests for SQLiteStorageProvider, JobRepository, and LegacyJsonMigrator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.storage.base import DatabaseProvider
from core.storage.factory import StorageFactory
from core.storage.migration import LegacyJsonMigrator
from core.storage.repository import JobRepository
from core.storage.sqlite import SQLiteStorageProvider
from core.store import ApplicationStore


@pytest.fixture
def memory_provider() -> SQLiteStorageProvider:
    return SQLiteStorageProvider(":memory:")


@pytest.fixture
def file_provider(tmp_path: Path) -> SQLiteStorageProvider:
    db_file = tmp_path / "radar.db"
    return SQLiteStorageProvider(db_file)


def test_sqlite_provider_crud(memory_provider: SQLiteStorageProvider) -> None:
    job = {
        "id": "celonis-1",
        "company": "Celonis",
        "title": "Security Engineer",
        "url": "https://example.com/job/1",
        "location": "Munich, Germany",
        "state": "discovered",
        "status": "ok",
        "favorited": False,
        "sources": [{"source": "Celonis", "url": "https://example.com/job/1"}],
        "tech_stack": ["Python", "AWS"],
    }

    # Upsert single
    memory_provider.upsert(job)
    assert memory_provider.count_all() == 1

    # Get by ID
    loaded = memory_provider.get_by_id("celonis-1")
    assert loaded is not None
    assert loaded["company"] == "Celonis"
    assert loaded["title"] == "Security Engineer"
    assert loaded["tech_stack"] == ["Python", "AWS"]
    assert loaded["favorited"] is False

    # Get by URL
    by_url = memory_provider.get_by_url("https://example.com/job/1")
    assert by_url is not None
    assert by_url["id"] == "celonis-1"

    # Update
    job["state"] = "parsed"
    job["final_score"] = 9.2
    job["favorited"] = True
    memory_provider.upsert(job)

    updated = memory_provider.get_by_id("celonis-1")
    assert updated is not None
    assert updated["state"] == "parsed"
    assert updated["final_score"] == 9.2
    assert updated["favorited"] is True

    # Delete
    assert memory_provider.delete("celonis-1") is True
    assert memory_provider.get_by_id("celonis-1") is None
    assert memory_provider.count_all() == 0
    assert memory_provider.delete("non-existent") is False


def test_sqlite_batch_upsert_and_state_counts(memory_provider: SQLiteStorageProvider) -> None:
    jobs = [
        {"id": "j1", "company": "A", "title": "T1", "state": "discovered", "status": "ok"},
        {"id": "j2", "company": "B", "title": "T2", "state": "parsed", "status": "ok"},
        {"id": "j3", "company": "C", "title": "T3", "state": "match", "status": "ok"},
        {"id": "j4", "company": "D", "title": "T4", "state": "discovered", "status": "failed"},
    ]

    memory_provider.upsert_batch(jobs)
    assert memory_provider.count_all() == 4

    counts = memory_provider.get_state_counts()
    assert counts["total"] == 4
    assert counts["discovered"] == 2
    assert counts["parsed"] == 1
    assert counts["match"] == 1
    assert counts["failed"] == 1

    # List with filtering
    discovered = memory_provider.list_jobs(state="discovered")
    assert len(discovered) == 2
    assert {j["id"] for j in discovered} == {"j1", "j4"}


def test_job_repository_operations(memory_provider: SQLiteStorageProvider) -> None:
    repo = JobRepository(memory_provider)
    repo.save({"id": "repo-1", "company": "Anthropic", "title": "Security SWE", "state": "discovered"})

    assert repo.count() == 1
    job = repo.get("repo-1")
    assert job is not None
    assert job["company"] == "Anthropic"

    assert repo.delete("repo-1") is True
    assert repo.count() == 0


def test_storage_factory(tmp_path: Path) -> None:
    provider = StorageFactory.create_provider(tmp_path, provider_type="sqlite")
    assert isinstance(provider, SQLiteStorageProvider)

    with pytest.raises(NotImplementedError):
        StorageFactory.create_provider(tmp_path, provider_type="postgres")

    with pytest.raises(ValueError):
        StorageFactory.create_provider(tmp_path, provider_type="unknown_db")


def test_legacy_json_migrator(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    json_path = artifacts_dir / "applications.json"

    legacy_data = [
        {
            "id": "celonis-it",
            "company": "Celonis",
            "title": "IT Engineer",
            "url": "https://example.com/1",
            "status": "new",  # legacy field without state
        },
        {
            "id": "sumup-swe",
            "company": "SumUp",
            "title": "Backend SWE",
            "url": "https://example.com/2",
            "state": "parsed",
            "status": "ok",
        },
    ]
    json_path.write_text(json.dumps(legacy_data))

    provider = SQLiteStorageProvider(artifacts_dir / "radar.db")
    migrator = LegacyJsonMigrator(tmp_path)

    migrated_count = migrator.migrate_if_needed(provider)
    assert migrated_count == 2
    assert provider.count_all() == 2

    # Check migrated legacy record
    item = provider.get_by_id("celonis-it")
    assert item is not None
    assert item["state"] == "discovered"
    assert item["status"] == "ok"

    # Check backup file created
    backup_path = artifacts_dir / "applications.json.migrated.bak"
    assert backup_path.exists()

    # Second run should be idempotent and return 0
    assert migrator.migrate_if_needed(provider) == 0


def test_application_store_delegation(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(exist_ok=True)
    store = ApplicationStore(artifacts / "applications.json")

    store.save([
        {"id": "app-1", "company": "TestCorp", "title": "SWE", "state": "discovered", "status": "ok"}
    ])

    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0]["id"] == "app-1"

    counts = store.state_counts()
    assert counts["total"] == 1
    assert counts["discovered"] == 1

    assert store.delete_job("app-1") is True
    assert len(store.load()) == 0

