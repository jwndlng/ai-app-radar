# Capability: Public Documentation

## Purpose

Ensure the repository presents accurately and professionally for public release: correct licensing, up-to-date README, removal of stale internal docs, contributor guidance, and a consistent project name.

## Requirements

### Requirement: Project has a MIT License
The repository SHALL include a LICENSE file containing the MIT license text with the correct copyright holder.

#### Scenario: License file exists
- **WHEN** a user visits the repository root
- **THEN** a LICENSE file is present containing MIT license text

### Requirement: README accurately describes the current tool
The README.md SHALL describe the current web-based pipeline, include a beta disclaimer, and present three distinct onboarding paths in the Getting Started section: (1) Claude Code using `/app:setup`, (2) Gemini CLI triggering the `app-setup` skill, and (3) manual setup following explicit shell commands. The quick start SHALL NOT describe `cp configs/companies.example.json configs/companies.json` (that file is deleted) and SHALL NOT reference `configs/companies.local.json`.

#### Scenario: README reflects current architecture
- **WHEN** a new user reads README.md
- **THEN** they see the web UI as the primary interface and three clearly labelled onboarding paths

#### Scenario: Beta disclaimer is visible
- **WHEN** a user opens README.md
- **THEN** a clearly visible disclaimer states this is an early-stage hobby project

#### Scenario: Claude Code path is documented
- **WHEN** a user reads the Getting Started section
- **THEN** they see instructions to open the repo in Claude Code and run `/app:setup`

#### Scenario: Gemini CLI path is documented
- **WHEN** a user reads the Getting Started section
- **THEN** they see instructions to open the repo in Gemini CLI and ask it to set up the application

#### Scenario: Manual path is documented
- **WHEN** a user reads the Getting Started section
- **THEN** they see explicit shell commands: `uv sync`, `playwright install chromium`, copy `.envrc.example` to `.envrc`, copy `profile.example.yaml` to `profile.yaml`, `make run`

#### Scenario: No companies.local.json references
- **WHEN** a user reads README.md
- **THEN** `companies.local.json` does not appear anywhere in the document

### Requirement: .envrc.example is committed
The repository SHALL include a `.envrc.example` file at the root showing all supported environment variable options with comments. It SHALL be the committed template for manual-path users, following the same copy-and-edit pattern as `configs/profile.example.yaml`.

#### Scenario: envrc.example present in repo
- **WHEN** a user clones the repository
- **THEN** `.envrc.example` is present and shows `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `LITELLM_BASE_URL`, `LITELLM_API_KEY`, `ADK_MODEL`, `PYTHONPATH`, and per-flow model override variables with comments explaining each

#### Scenario: Manual-path user copies template
- **WHEN** a user follows the manual setup path
- **THEN** they can run `cp .envrc.example .envrc` and fill in their key, matching the same pattern as the profile setup

### Requirement: CONTRIBUTING.md sets contributor expectations
The repository SHALL include a CONTRIBUTING.md that describes how to report issues, submit PRs, and sets an explicit expectation of response latency for a hobby project.

#### Scenario: Contribution guide exists
- **WHEN** a user wants to contribute
- **THEN** CONTRIBUTING.md explains the process and notes that this is a hobby project with no SLA on responses

### Requirement: Project name is consistent
The project name "AI-powered Application Radar" SHALL be used consistently in README.md and pyproject.toml.

#### Scenario: pyproject.toml uses canonical name
- **WHEN** the project is installed or referenced
- **THEN** pyproject.toml `name` field is `ai-app-radar`
