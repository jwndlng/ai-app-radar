# Specification: Database Storage Provider

## Purpose
Establishing a pluggable, robust database storage architecture with an embedded SQLite default (WAL mode) and repository pattern to ensure fast queries, concurrency isolation, and extensibility.

## Requirements

### Requirement: Database Provider Interface
The storage layer SHALL define an abstract `DatabaseProvider` interface declaring CRUD and query operations for job persistence, including `get_by_id`, `get_by_url`, `list_jobs`, `upsert`, `upsert_batch`, `delete`, and `get_state_counts`.

#### Scenario: Provider abstraction usage
- **WHEN** any pipeline consumer or API route interacts with job persistence
- **THEN** it SHALL interact solely through the provider or repository abstraction without issuing engine-specific SQL directly.

### Requirement: SQLite Concrete Provider Implementation
The system SHALL provide a concrete `SQLiteStorageProvider` that implements `DatabaseProvider` using the standard library `sqlite3` driver.

#### Scenario: SQLite WAL initialization
- **WHEN** `SQLiteStorageProvider` establishes a database connection
- **THEN** it SHALL configure `PRAGMA journal_mode = WAL`, `PRAGMA busy_timeout = 5000`, `PRAGMA synchronous = NORMAL`, and `PRAGMA foreign_keys = ON`.

### Requirement: Hybrid Relational and JSON Schema
The `applications` table SHALL store queryable filter fields (`id`, `hash_id`, `company`, `title`, `url`, `location`, `state`, `status`, `final_score`, `location_score`, `seniority_score`, `favorited`, `discovered_at`, `updated_at`, `vetted_at`, `archived_at`, `error_message`) as indexed columns, and unstructured fields (`sources`, `tech_stack`, `domains`, `key_responsibilities`, `required_qualifications`, `reasons`, `matched_skills`, `description`) in a `data` JSON column.

#### Scenario: Upserting and retrieving hybrid job record
- **WHEN** a job dictionary is saved via `upsert`
- **THEN** top-level relational attributes SHALL be stored in indexed columns and remaining nested attributes SHALL be serialized to the `data` column, with `get_by_id` deserializing and combining them seamlessly into a dictionary matching the original schema.

### Requirement: Concurrency and Transaction Safety
The storage provider SHALL execute batch writes within explicit ACID transactions and handle concurrent access gracefully.

#### Scenario: Concurrent pipeline checkpoints
- **WHEN** background consumers save progress checkpoints while web endpoints read or update job states
- **THEN** transactions SHALL not block reads and locks SHALL wait up to 5000ms before timing out, preventing file-clobbering and locking errors.

### Requirement: State Count Aggregation
The storage provider SHALL provide a fast aggregation method `get_state_counts()` that computes counts grouped by state in a single query.

#### Scenario: Dashboard stats calculation
- **WHEN** state statistics are requested by the API or frontend
- **THEN** the provider SHALL execute an indexed SQL aggregation query and return counts for each state without loading full row payloads into memory.

