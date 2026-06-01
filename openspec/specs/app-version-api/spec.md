# app-version-api

## Purpose

Exposes the running application version via a REST endpoint and sets matching metadata on the FastAPI application instance, sourced from the `APP_VERSION` environment variable.

## Requirements

### Requirement: GET /api/version returns running app version
The API SHALL expose a `GET /api/version` endpoint that returns the value of the `APP_VERSION`
environment variable as a JSON object. When `APP_VERSION` is not set, the endpoint SHALL
return `"dev"`.

#### Scenario: Tagged release build
- **WHEN** the app is running in a container built from a tagged commit (e.g. `v0.2.1`)
- **THEN** `GET /api/version` returns `{ "version": "v0.2.1" }` with HTTP 200

#### Scenario: Untagged main build
- **WHEN** the app is running in a container built from an untagged commit
- **THEN** `GET /api/version` returns `{ "version": "<git-describe-output>" }` with HTTP 200

#### Scenario: Local dev (no APP_VERSION set)
- **WHEN** the app is started locally without the `APP_VERSION` env var
- **THEN** `GET /api/version` returns `{ "version": "dev" }` with HTTP 200

### Requirement: FastAPI app version metadata matches APP_VERSION
The `FastAPI` application instance SHALL be initialised with `version` set to the value of
the `APP_VERSION` environment variable (default `"dev"`), replacing the previously hardcoded
`"1.0.0"`.

#### Scenario: OpenAPI metadata reflects runtime version
- **WHEN** the app starts with `APP_VERSION=v0.2.1`
- **THEN** the `/openapi.json` schema contains `"version": "v0.2.1"`
