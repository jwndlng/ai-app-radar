# Capability: ci-release

## Purpose

GitHub Actions workflows that build, tag, and publish the Docker image to GHCR on every push to `main` and on version tag pushes.

## Requirements

### Requirement: GitHub Actions workflow builds and pushes image on push to main
The repository SHALL contain a GitHub Actions workflow at `.github/workflows/docker.yml` that triggers on every push to the `main` branch, builds the Docker image, and pushes it to GHCR with the tag `latest`.

#### Scenario: Push to main publishes latest
- **WHEN** a commit is pushed to the `main` branch
- **THEN** the workflow runs, builds the image, and `ghcr.io/<owner>/ai-app-radar:latest` is updated on GHCR

#### Scenario: Workflow uses GITHUB_TOKEN for GHCR auth
- **WHEN** the workflow runs in the GitHub Actions context
- **THEN** it authenticates to GHCR using the built-in `GITHUB_TOKEN` with no additional secrets required

### Requirement: Workflow publishes versioned image on v* tag push
The same workflow SHALL also trigger on tag pushes matching `v*`. When triggered by a tag, it SHALL push the image with both the exact tag (e.g., `v1.2.0`) and `latest`.

#### Scenario: Tag push publishes versioned image
- **WHEN** a tag matching `v*` (e.g., `v1.2.0`) is pushed to the repository
- **THEN** the workflow builds and pushes `ghcr.io/<owner>/ai-app-radar:v1.2.0` and `ghcr.io/<owner>/ai-app-radar:latest`

#### Scenario: Non-v tag does not trigger release
- **WHEN** a tag not matching `v*` (e.g., `experiment-1`) is pushed
- **THEN** the docker workflow does not run

### Requirement: APP_VERSION build arg set from git describe at CI time
The workflow SHALL pass `APP_VERSION` as a Docker build argument, resolved by running `git describe --tags --always` on the checked-out commit. This value SHALL be visible in the built image as both the OCI version label and the `APP_VERSION` env var.

#### Scenario: Version label matches git tag on tagged build
- **WHEN** the workflow is triggered by pushing tag `v1.3.0`
- **THEN** the built image carries `org.opencontainers.image.version=v1.3.0`

#### Scenario: Version label is a hash on untagged main push
- **WHEN** the workflow is triggered by a push to main with no tag on the commit
- **THEN** the built image carries a version label of the form `<last-tag>-<n>-g<hash>` (output of `git describe --tags --always`)

### Requirement: Workflow runs only on repository-owned events
The workflow SHALL use `permissions: packages: write` and `contents: read` and SHALL NOT expose secrets beyond what is required for GHCR push. It SHALL NOT run on pull requests from forks to prevent secret exposure.

#### Scenario: Fork PR does not trigger docker build
- **WHEN** a pull request is opened from a fork
- **THEN** the docker workflow does not run (trigger is push, not pull_request)
