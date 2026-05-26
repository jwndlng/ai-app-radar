# Capability: docker-image

## Purpose

A self-contained Docker image and associated compose configuration that lets users run the full application (web server + pipeline operations) without any local Python environment.

## Requirements

### Requirement: Dockerfile builds a runnable image
The repository SHALL contain a `Dockerfile` that produces a self-contained image capable of running the web server and all pipeline operations without any local Python environment or dependency installation by the user.

#### Scenario: Image builds from clean checkout
- **WHEN** `docker build .` is run from the repository root on a machine with no prior build cache
- **THEN** the build completes without error and produces a tagged image

#### Scenario: Web server starts inside container
- **WHEN** the image is run with `docker run -p 8000:8000 --env-file .env <image>`
- **THEN** the FastAPI server starts and responds on port 8000

### Requirement: Dependency installation uses uv with frozen lockfile
The Dockerfile SHALL install Python dependencies using `uv sync --no-dev --frozen` against the committed `uv.lock`, ensuring reproducible builds. The installed venv SHALL be on `PATH` so all `python` and entry-point invocations resolve to it.

#### Scenario: Build fails on lockfile drift
- **WHEN** `pyproject.toml` lists a dependency not present in `uv.lock`
- **THEN** the Docker build fails at the `uv sync` step with a clear error

#### Scenario: Dev dependencies absent from image
- **WHEN** the image is inspected after a successful build
- **THEN** `pytest` and other dev-only packages are not importable inside the container

### Requirement: Playwright Chromium installed with system dependencies
The Dockerfile SHALL run `playwright install chromium --with-deps` so that web scraping via Playwright works inside the container. Only Chromium SHALL be installed (not Firefox or WebKit).

#### Scenario: Playwright can launch Chromium headlessly
- **WHEN** a pipeline scout operation is triggered inside the running container
- **THEN** Playwright launches Chromium without missing-library errors

### Requirement: Version baked into image at build time
The Dockerfile SHALL accept an `APP_VERSION` build argument (default `dev`) and expose it as both an OCI label (`org.opencontainers.image.version`) and an environment variable (`APP_VERSION`) inside the container.

#### Scenario: Tagged build carries correct version
- **WHEN** the image is built with `--build-arg APP_VERSION=v1.2.0`
- **THEN** `docker inspect <image>` shows `org.opencontainers.image.version=v1.2.0` and the env var `APP_VERSION=v1.2.0` is set inside the container

#### Scenario: Untagged local build defaults to dev
- **WHEN** the image is built without `--build-arg APP_VERSION`
- **THEN** the label and env var both show `dev`

### Requirement: configs and artifacts declared as volume mount points
The Dockerfile SHALL declare `/app/configs` and `/app/artifacts` as `VOLUME` entries. The image SHALL ship default `companies.json` and `settings.yaml` inside `/app/configs` so the container is functional without any mount. `profile.yaml` SHALL NOT be shipped in the image.

#### Scenario: Container starts without any volume mounts
- **WHEN** the container is run with no `-v` flags and a valid `profile.yaml` is absent
- **THEN** the server starts but returns an error when a profile-dependent operation is attempted (not at container startup)

#### Scenario: User config overrides image defaults
- **WHEN** the user mounts a local `configs/` directory containing their `profile.yaml`
- **THEN** the app uses the mounted `profile.yaml` and the user's version of `companies.json` if present

### Requirement: .dockerignore excludes runtime and development artifacts
A `.dockerignore` file SHALL exclude `.venv/`, `artifacts/`, `logs/`, `configs/profile.yaml`, `tests/`, `tuning/`, and `openspec/` from the build context to keep the image lean and avoid leaking personal data.

#### Scenario: profile.yaml not present in built image
- **WHEN** the image is built from a working directory that contains `configs/profile.yaml`
- **THEN** the file is not present inside the built image

### Requirement: docker-compose.yml for zero-friction local startup
The repository SHALL contain a `docker-compose.yml` at the repo root that pulls the GHCR image, mounts `./configs` and `./artifacts` as volumes, binds port 8000, and loads API keys from a `.env` file. This SHALL be the canonical way to run the application locally — users need only fill in `profile.yaml` and run `docker compose up`.

#### Scenario: docker compose up starts the dashboard
- **WHEN** a user with Docker installed runs `docker compose up` from the repo root with `configs/profile.yaml` present and `.env` containing their API keys
- **THEN** the web dashboard is accessible at `http://localhost:8000` without any local Python setup

#### Scenario: Stopping removes the container but preserves data
- **WHEN** the user runs `docker compose down`
- **THEN** the container is removed but `./configs` and `./artifacts` on the host are untouched
