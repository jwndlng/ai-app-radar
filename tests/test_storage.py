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


def test_sqlite_projections_and_search(memory_provider: SQLiteStorageProvider) -> None:
    job1 = {
        "id": "j-sec",
        "company": "Anthropic",
        "title": "Software Security Engineer",
        "location": "Remote",
        "state": "match",
        "status": "ok",
        "final_score": 9.5,
        "favorited": True,
        "description": "Deep security engineering analysis text...",
        "reasons": ["Top tier match", "Python & Rust"],
        "tech_stack": ["Python", "Rust"],
    }
    job2 = {
        "id": "j-infra",
        "company": "OpenAI",
        "title": "Infrastructure Architect",
        "location": "San Francisco",
        "state": "match",
        "status": "ok",
        "final_score": 7.0,
        "favorited": False,
        "description": "Large scale cluster management...",
        "reasons": ["Good fit"],
        "tech_stack": ["Kubernetes"],
    }

    memory_provider.upsert_batch([job1, job2])

    # Summary projection should omit deep fields
    summaries = memory_provider.list_jobs(projection="summary")
    assert len(summaries) == 2
    for s in summaries:
        assert "description" not in s
        assert "reasons" not in s
        assert "tech_stack" not in s
        assert "company" in s
        assert "title" in s

    # Full projection should include deep fields
    full_jobs = memory_provider.list_jobs(projection="full")
    assert len(full_jobs) == 2
    sec_job = next(j for j in full_jobs if j["id"] == "j-sec")
    assert sec_job["description"] == "Deep security engineering analysis text..."
    assert sec_job["reasons"] == ["Top tier match", "Python & Rust"]

    # Search filter
    search_results = memory_provider.list_jobs(search="security")
    assert len(search_results) == 1
    assert search_results[0]["id"] == "j-sec"

    # Favorited only
    fav_results = memory_provider.list_jobs(favorited_only=True)
    assert len(fav_results) == 1
    assert fav_results[0]["id"] == "j-sec"

    # Sorting
    sorted_by_score = memory_provider.list_jobs(sort_by="score", sort_order="desc")
    assert sorted_by_score[0]["id"] == "j-sec"
    assert sorted_by_score[1]["id"] == "j-infra"


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


def test_summary_projection_exposes_ui_data_fields(memory_provider: SQLiteStorageProvider) -> None:
    """score, salary_range, and compensation_score live in the data blob but
    are rendered on collapsed job cards, so the summary projection must
    surface them."""
    memory_provider.upsert({
        "id": "acme-eng",
        "company": "Acme",
        "title": "Engineer",
        "state": "review",
        "status": "ok",
        "score": 7.2,
        "salary_range": "100-120k",
        "compensation_score": 6.0,
        "description": "long text",
    })

    rows = memory_provider.list_jobs(projection="summary")
    assert rows[0]["score"] == 7.2
    assert rows[0]["salary_range"] == "100-120k"
    assert rows[0]["compensation_score"] == 6.0
    assert "description" not in rows[0]


def test_list_jobs_offset_without_limit(memory_provider: SQLiteStorageProvider) -> None:
    for i in range(5):
        memory_provider.upsert({
            "id": f"c-{i}", "company": "C", "title": f"T{i}",
            "state": "discovered", "status": "ok",
            "updated_at": f"2026-08-0{i + 1}T00:00:00",
        })

    page = memory_provider.list_jobs(offset=3)
    assert len(page) == 2


def test_migrator_moves_legacy_file_so_it_cannot_reimport(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    legacy = artifacts / "applications.json"
    legacy.write_text(json.dumps([{"id": "old-1", "company": "A", "title": "T", "state": "rejected", "status": "ok"}]))

    provider = SQLiteStorageProvider(artifacts / "radar.db")
    assert LegacyJsonMigrator(tmp_path).migrate_if_needed(provider) == 1
    # Original moved to backup: an emptied table must not resurrect the jobs.
    assert not legacy.exists()
    assert (artifacts / "applications.json.migrated.bak").exists()

    provider.delete("old-1")
    assert LegacyJsonMigrator(tmp_path).migrate_if_needed(provider) == 0
    assert provider.count_all() == 0


def test_migrator_moves_file_even_when_db_already_populated(tmp_path: Path) -> None:
    """A leftover legacy file (migrated under old copy-based code) must be
    moved aside on the populated-DB path too, or an emptied table would
    silently re-import the stale snapshot."""
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    legacy = artifacts / "applications.json"
    legacy.write_text(json.dumps([{"id": "stale", "company": "A", "title": "T",
                                   "state": "rejected", "status": "ok"}]))

    provider = SQLiteStorageProvider(artifacts / "radar.db")
    provider.upsert({"id": "live", "company": "B", "title": "U", "state": "review", "status": "ok"})

    assert LegacyJsonMigrator(tmp_path).migrate_if_needed(provider) == 0
    assert not legacy.exists()

    provider.delete("live")
    assert LegacyJsonMigrator(tmp_path).migrate_if_needed(provider) == 0
    assert provider.count_all() == 0
