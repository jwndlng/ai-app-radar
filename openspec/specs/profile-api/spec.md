# Spec: profile-api

## Purpose

REST API endpoints for reading and writing the user profile (`configs/profile.yaml`), including atomic saves with automatic backup and backup restoration.

## Requirements

### Requirement: GET /api/profile returns parsed profile as JSON
`GET /api/profile` SHALL read `configs/profile.yaml`, parse it, and return the full profile as a JSON object. The response structure mirrors the YAML structure exactly.

#### Scenario: Profile loads successfully
- **WHEN** `GET /api/profile` is called and `configs/profile.yaml` exists
- **THEN** the response is a JSON object with the full profile data and HTTP 200

#### Scenario: Missing profile returns 404
- **WHEN** `GET /api/profile` is called and `configs/profile.yaml` does not exist
- **THEN** the response is HTTP 404 with `{ "detail": "Profile not found" }`

### Requirement: PUT /api/profile writes profile atomically with backup
`PUT /api/profile` SHALL accept a JSON body representing the full profile, create a timestamped backup of the current `configs/profile.yaml` to `configs/backups/profile_<ISO8601>.yaml` before writing, then overwrite `configs/profile.yaml` with the new content serialised as YAML. After writing, it SHALL prune backups older than the 10 most recent.

#### Scenario: Profile is saved and backup created
- **WHEN** `PUT /api/profile` is called with a valid profile JSON body
- **THEN** the current profile is backed up to `configs/backups/`, the new profile is written to `configs/profile.yaml`, and the response is `{ "ok": true }`

#### Scenario: Backup directory is created if missing
- **WHEN** `PUT /api/profile` is called and `configs/backups/` does not exist
- **THEN** the directory is created before writing the backup

#### Scenario: Old backups are pruned after write
- **WHEN** more than 10 backup files exist after a write
- **THEN** the oldest files beyond the 10 most recent are deleted

#### Scenario: YAML comments are not preserved
- **WHEN** the profile is saved via PUT
- **THEN** `configs/profile.yaml` is valid YAML containing all data, but inline comments from the original file are not preserved (accepted limitation)

### Requirement: GET /api/profile/backups returns backup list
`GET /api/profile/backups` SHALL return a list of available backup files sorted by creation time descending, with each entry containing `filename` and `created_at` (ISO8601 string).

#### Scenario: Backups listed in reverse chronological order
- **WHEN** `GET /api/profile/backups` is called with 3 backups present
- **THEN** the response contains 3 entries sorted newest-first with `filename` and `created_at` fields

#### Scenario: No backups returns empty list
- **WHEN** `GET /api/profile/backups` is called and no backups exist
- **THEN** the response is `{ "backups": [] }`

### Requirement: POST /api/profile/backups/restore restores a backup
`POST /api/profile/backups/restore` SHALL accept `{ "filename": "<backup_filename>" }`, validate the file exists in `configs/backups/`, create a backup of the current profile before restoring, then copy the backup file to `configs/profile.yaml`.

#### Scenario: Restore succeeds and backs up current state first
- **WHEN** `POST /api/profile/backups/restore` is called with a valid filename
- **THEN** the current profile is backed up, the backup file content is written to `configs/profile.yaml`, and the response is `{ "ok": true, "restored": "<filename>" }`

#### Scenario: Unknown filename returns 404
- **WHEN** `POST /api/profile/backups/restore` is called with a filename not in `configs/backups/`
- **THEN** the response is HTTP 404 with `{ "detail": "Backup not found" }`

#### Scenario: Path traversal is rejected
- **WHEN** `POST /api/profile/backups/restore` is called with a filename containing `..` or `/`
- **THEN** the response is HTTP 400 with `{ "detail": "Invalid filename" }`
