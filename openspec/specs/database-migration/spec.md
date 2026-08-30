# Specification: Database Migration

## Purpose
Automating schema bootstrapping and zero-downtime, idempotent data migration from legacy `applications.json` to the active database provider.

## Requirements

### Requirement: Idempotent Legacy JSON Data Migration
The system SHALL provide an automated migration mechanism that reads `artifacts/applications.json` and imports all records into the active database provider if the database is uninitialized or empty.

#### Scenario: First boot with existing applications.json
- **WHEN** the application starts with an empty SQLite database and an existing `artifacts/applications.json` file
- **THEN** all job records SHALL be migrated into the database in a single atomic transaction.

#### Scenario: Subsequent boots
- **WHEN** the database already contains records
- **THEN** the migration runner SHALL skip re-importing to prevent overwriting updated records.

### Requirement: Migration Backup Preservation
The migration process SHALL preserve the original JSON data by creating a backup copy before completing the migration.

#### Scenario: Preserving JSON backup
- **WHEN** the migration of `applications.json` completes successfully
- **THEN** the original file SHALL be safely backed up to `artifacts/applications.json.migrated.bak`.

