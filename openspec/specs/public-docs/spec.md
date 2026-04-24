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
The README.md SHALL describe the current web-based pipeline (not the old CLI), include a beta disclaimer, cover quick start, pipeline overview, configuration, and contributing guidance.

#### Scenario: README reflects current architecture
- **WHEN** a new user reads README.md
- **THEN** they see the web UI as the primary interface, not a CLI report command

#### Scenario: Beta disclaimer is visible
- **WHEN** a user opens README.md
- **THEN** a clearly visible disclaimer states this is an early-stage hobby project and usage is at the user's own risk

#### Scenario: Quick start is actionable
- **WHEN** a user follows the Quick Start section
- **THEN** they can get the web UI running with `uv sync`, `uv run playwright install chromium`, and `make run` (or equivalent)

#### Scenario: Pipeline stages are explained
- **WHEN** a user reads the pipeline section
- **THEN** Scout, Enrich, and Evaluate stages are each described with their purpose and configuration file

### Requirement: Stale internal docs are removed
AGENT.md, SCOUT.md, and EVALUATION.md SHALL be deleted from the repository as they describe an architecture that no longer exists.

#### Scenario: Old docs are absent
- **WHEN** a user browses the repository
- **THEN** AGENT.md, SCOUT.md, and EVALUATION.md are not present

### Requirement: CONTRIBUTING.md sets contributor expectations
The repository SHALL include a CONTRIBUTING.md that describes how to report issues, submit PRs, and sets an explicit expectation of response latency for a hobby project.

#### Scenario: Contribution guide exists
- **WHEN** a user wants to contribute
- **THEN** CONTRIBUTING.md explains the process and notes that this is a hobby project with no SLA on responses

### Requirement: Project name is consistent
The project name "Agentic Application Tracker" SHALL be used consistently in README.md and pyproject.toml.

#### Scenario: pyproject.toml uses canonical name
- **WHEN** the project is installed or referenced
- **THEN** pyproject.toml `name` field is `agentic-application-tracker`
