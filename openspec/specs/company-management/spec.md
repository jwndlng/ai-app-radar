# Specification: Company Management Capability

## Purpose

To provide read/write access to the configured company list, enabling the pipeline and UI to list companies and mutate their enabled state.

## Requirements

### Requirement: List all companies
The system SHALL expose a way to retrieve all configured companies, including their enabled state and metadata.

### Requirement: Toggle company enabled state
The system SHALL allow toggling the `enabled` flag of a configured company, persisting the change to the company configuration store.

### Requirement: PipelineRunner owns company read/write
All reads from and writes to the company configuration SHALL go through `PipelineRunner` (or a dedicated service it owns), ensuring a single point of access and consistency guarantees.
