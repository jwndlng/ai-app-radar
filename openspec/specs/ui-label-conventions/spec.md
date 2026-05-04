# Spec: UI Label Conventions

## Purpose

Defines consistent labeling conventions for pipeline stages, actions, and state-reversal controls throughout the UI.

## Requirements

### Requirement: Pipeline stage one is labeled "Discovery"
The first pipeline stage SHALL be labeled "Discovery" in all visible UI text. This includes the pipeline action card title and label, the pipeline flow sidebar node, and the operation name shown in the Running Tasks panel for scout operations. Backend identifiers (`discovered`, `/api/scout`) are unchanged.

#### Scenario: Pipeline card shows Discovery
- **WHEN** a user views the pipeline action area
- **THEN** the first stage card is labeled "① Discovery" and titled "Find roles"

#### Scenario: Task panel shows Discovery operation
- **WHEN** a scout operation appears in the Running Tasks panel
- **THEN** the operation name displays as "Discovery" not "Scout"

#### Scenario: Sidebar pipeline node shows Discovery
- **WHEN** a user views the pipeline flow in the sidebar
- **THEN** the first stage node is labeled "Discovery"

### Requirement: State-reversal action label reflects the target pipeline stage
The per-job state-reversal button SHALL show a context-aware label: "Re-enrich" when the job is in `parsed` state, and "Re-evaluate" when the job is in any post-evaluate state (match, review, applied, rejected, archived). The bulk state-reversal control in the pipeline secondary actions row SHALL be labeled "Revert all". Neither SHALL use the word "Undo".

#### Scenario: Per-job button shows Re-enrich for parsed jobs
- **WHEN** a user views the action buttons on a job card in the "parsed" state
- **THEN** the state-reversal button is labeled "Re-enrich"

#### Scenario: Per-job button shows Re-evaluate for evaluated jobs
- **WHEN** a user views the action buttons on a job card in match, review, applied, rejected, or archived state
- **THEN** the state-reversal button is labeled "Re-evaluate"

#### Scenario: Pipeline secondary shows Revert all
- **WHEN** a user views the pipeline secondary actions row
- **THEN** the bulk reversal control label reads "Revert all"

#### Scenario: Revert absent on discovered jobs
- **WHEN** a job is in the "discovered" state
- **THEN** no state-reversal button is shown (nothing to revert to)
