# Specification: Restructuring (Agentic Application Process)

## Purpose
Define the foundational architecture for the "Application as Code" process, ensuring a clean separation between LaTeX assets, agentic logic, and job tracking state.

## Requirements

### Requirement: Asset Centralization (LaTeX)
The system SHALL consolidate all LaTeX-related files into a `latex/` tree to isolate the "build layer" from the "process layer."

#### Scenario: Sub-directory relocation
- **GIVEN** a resume folder `resume_<name>` in the root
- **THEN** it SHALL be moved to `latex/resumes/<name>/`
- **AND** the CI/CD pipeline SHALL be updated to discover `latex/resumes/*/main.tex`.

### Requirement: Schema-Compliant Tracking
All job tracking artifacts in the `applications/` directory SHALL strictly adhere to the YAML schemas defined in the Design documentation.

#### Scenario: State Transition Atomic Move
- **GIVEN** a job entry identified by `id` in `new.yaml`
- **WHEN** the `evaluate` flow completes
- **THEN** the entry SHALL be deleted from `new.yaml`
- **AND** it SHALL be appended to `in_progress.yaml`
- **AND** the `status` field SHALL be assigned exactly one of the valid states: [`evaluation`, `match`, `intel`, `ready-to-apply`].

### Requirement: Discovery Rule Isolation
The system SHALL isolate search and filtering rules into `configs/scout.yaml`.

#### Scenario: Rule-based Scout
- **WHEN** the `scout` flow is executed
- **THEN** it SHALL read the `keywords` and `portals` from `configs/scout.yaml`
- **AND** its output SHALL only be appended to `applications/new.yaml`.

### Requirement: Build System Stability
The LuaLaTeX build process SHALL be agnostic of the root-level restructuring.

#### Scenario: Path Resolution
- **WHEN** `lualatex main.tex` is executed inside any `latex/resumes/*/` directory
- **THEN** it SHALL resolve all `\input` dependencies and image assets (e.g., `media/`) successfully.

### Requirement: Python source lives under src/
All Python source packages SHALL reside under a `src/` directory at the repo root. The repo root SHALL contain only `pyproject.toml`, `uv.lock`, `Makefile`, and non-Python directories (`configs/`, `artifacts/`, `openspec/`, `latex/`). No Python package directory SHALL exist directly at the repo root.

#### Scenario: Source tree is rooted under src/
- **WHEN** listing the repo root
- **THEN** no Python package directories (`flows/`, `common/`, `tests/`) SHALL appear at the top level; only `src/` SHALL contain them

#### Scenario: uv run invocations are unchanged
- **WHEN** `uv run python -m flows.scout.main` is executed from the repo root
- **THEN** it resolves correctly because `src/` is on PYTHONPATH

### Requirement: common/ is a top-level package independent of flows/
The `common/` package SHALL be located at `src/common/`, not inside `src/flows/`. It SHALL be importable as `common.*` without any `flows.` prefix. No flow package SHALL add it to `sys.path` manually.

#### Scenario: Importing from common
- **WHEN** a flow module does `from common.cli import call_gemini_cli`
- **THEN** Python resolves it without any `sys.path` manipulation

#### Scenario: common is not nested under flows
- **WHEN** listing `src/flows/`
- **THEN** no `common/` subdirectory SHALL exist inside it

### Requirement: No sys.path manipulation in flow modules
Flow modules SHALL NOT use `sys.path.append` or `sys.path.insert` to resolve imports. All inter-package imports SHALL rely solely on `PYTHONPATH=src` being set in the environment.

#### Scenario: Flow module imports common without path hack
- **WHEN** `src/flows/enrich/main.py` is read
- **THEN** no `sys.path.append` call SHALL be present; `from common.cli import ...` SHALL be used directly

#### Scenario: Scout module imports its own providers without path hack
- **WHEN** `src/flows/scout/scout.py` is read
- **THEN** no `sys.path.append` call SHALL be present

### Requirement: PYTHONPATH configured for both runtime and test execution
`src/` SHALL be added to `PYTHONPATH` in two places: `.envrc` (for shell/uv runtime) and `pyproject.toml` `[tool.pytest.ini_options]` (for pytest). Both SHALL be kept in sync so that `uv run` and `uv run pytest` resolve packages identically.

#### Scenario: pytest resolves src packages
- **WHEN** `uv run pytest` is run from the repo root
- **THEN** `src/common/` and `src/flows/` are importable in tests without additional configuration

#### Scenario: .envrc sets PYTHONPATH
- **WHEN** direnv loads `.envrc`
- **THEN** `PYTHONPATH` includes `src` so that `uv run python -m flows.*` works

### Requirement: tests/ resides inside src/
The `tests/` directory SHALL be located at `src/tests/`. pytest's `testpaths` SHALL be configured to `["src/tests"]` in `pyproject.toml`.

#### Scenario: pytest discovers tests from src/tests/
- **WHEN** `uv run pytest` is run
- **THEN** test files under `src/tests/` are discovered and executed
