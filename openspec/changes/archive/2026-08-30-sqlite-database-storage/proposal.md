## Why

The application currently relies on a single monolithic `artifacts/applications.json` file for all job state persistence. Every read and write performs a full $O(N)$ serialization/deserialization pass, leading to UI latency, severe performance degradation as the dataset grows, and write-clobbering race conditions between background pipeline workers and API operations.

Migrating to a robust, pluggable database architecture with an embedded SQLite default (configured in WAL mode) provides instant query performance, ACID transactions, and concurrency isolation, while establishing an extensible provider interface for future relational database engines like PostgreSQL.

## What Changes

- Introduce a pluggable `DatabaseProvider` interface and repository pattern in `src/core/store.py` (or `src/core/storage/`) to abstract database operations.
- Implement `SQLiteStorageProvider` as the default embedded engine with Write-Ahead Logging (WAL mode), busy timeout handling, and foreign key enforcement.
- Implement hybrid storage: structured, indexed columns for queryable metadata (`id`, `hash_id`, `company`, `title`, `url`, `state`, `status`, `final_score`, `location_score`, `seniority_score`, `favorited`, timestamps) combined with a JSON column for rich nested payloads (tech stack, responsibilities, qualifications, scoring reasoning).
- Implement automatic schema initialization and an idempotent one-time migration runner from legacy `artifacts/applications.json` to the database.
- Add configuration support in `configs/settings.yaml` / environment variables to select and configure the database provider (`sqlite` as default, ready for `postgres`).
- Update all consumers (`ScoutConsumer`, `EnrichConsumer`, `EvaluateConsumer`), pipeline runners, and API dependencies to interact through the repository abstraction.
- Keep existing `ApplicationStore` API backward-compatible during the transition or adapt callers cleanly to the new provider abstraction.

## Capabilities

### New Capabilities
- `database-storage-provider`: Abstract storage interface and concrete SQLite provider implementation supporting indexed lookups, filtering, atomic updates, and pluggability for other relational databases (e.g. Postgres).
- `database-migration`: Automatic schema bootstrapping and zero-downtime data migration from legacy `applications.json` to the active database provider.

### Modified Capabilities
<!-- None: existing spec requirements remain preserved while underlying persistence is modernized. -->

## Impact

- **Storage Layer**: `src/core/store.py`, `src/core/storage/`
- **Pipeline Consumers & Runners**: `src/scout/consumer.py`, `src/scout/state_tracker.py`, `src/enrich/consumer.py`, `src/evaluate/consumer.py`, `src/maintenance/archiver.py`, `src/repair/repair.py`, `src/api/deps.py`
- **API Endpoints**: `src/api/routes.py`
- **Configuration**: `src/core/config.py`, `configs/settings.yaml`
- **Dependencies**: Python standard library `sqlite3` (zero new external dependencies for SQLite).

