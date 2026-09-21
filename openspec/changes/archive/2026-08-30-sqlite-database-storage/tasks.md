## 1. Storage Provider Architecture & Base Interfaces

- [x] 1.1 Create `src/core/storage/` module with abstract `DatabaseProvider` base class defining CRUD, batch upsert, and state aggregation signatures.
- [x] 1.2 Implement high-level `JobRepository` in `src/core/storage/repository.py` wrapping the provider and handling model transformations.
- [x] 1.3 Implement provider factory `get_database_provider(root_dir, config)` defaulting to SQLite with architectural hooks for PostgreSQL.

## 2. SQLite Concrete Engine Implementation

- [x] 2.1 Implement `SQLiteStorageProvider` in `src/core/storage/sqlite.py` with WAL mode, `PRAGMA busy_timeout = 5000`, and connection context managers.
- [x] 2.2 Define and execute the hybrid relational + JSON table schema (`applications` table and indexes on `state`, `status`, `url`, `company`, `updated_at`, `final_score`).
- [x] 2.3 Implement single-job and batch upsert operations with proper JSON serialization/deserialization.
- [x] 2.4 Implement indexed query methods (`get_by_id`, `get_by_url`, `list_jobs`, `delete`) and state count aggregation (`get_state_counts`).

## 3. Legacy Data Migration & Store Compatibility Layer

- [x] 3.1 Implement `LegacyJsonMigrator` in `src/core/storage/migration.py` to idempotently import `artifacts/applications.json` into SQLite on first startup.
- [x] 3.2 Ensure migrated source JSON is safely preserved as `artifacts/applications.json.migrated.bak`.
- [x] 3.3 Update `src/core/store.py` (`ApplicationStore`) to wrap `JobRepository` ensuring seamless backward compatibility for existing callers.

## 4. Pipeline Components & API Integration

- [x] 4.1 Update `src/scout/state_tracker.py` and `src/scout/consumer.py` to query and persist jobs through the repository.
- [x] 4.2 Update `src/enrich/consumer.py` and `src/evaluate/consumer.py` to use repository batch checkpointing.
- [x] 4.3 Update `src/maintenance/archiver.py` and `src/repair/repair.py` to query and update jobs via the repository.
- [x] 4.4 Update `src/api/deps.py` and `src/api/routes.py` to utilize repository methods and add optimized stats handling.

## 5. Verification & Test Suite

- [x] 5.1 Add unit tests for `SQLiteStorageProvider` and `JobRepository` testing CRUD, concurrency, and hybrid JSON serialization.
- [x] 5.2 Add unit tests for `LegacyJsonMigrator` verifying idempotent data migration and backup creation.
- [x] 5.3 Update existing tests (`tests/test_tracker.py`, `tests/test_archiver.py`, etc.) to run with the new database storage backend.
- [x] 5.4 Run full automated test suite to ensure zero regressions across all pipeline flows.
