# Specification: Tuning Judge Capability

## Purpose
To compare job result sets produced by multiple models, identify consensus and divergence, and produce a structured analysis for the tuning harness.

## Requirements

### Requirement: Judge compares all model result sets and produces structured analysis
The `TuneJudge` agent SHALL accept all model job lists as input and return a structured analysis identifying consensus jobs, model-unique jobs, pagination drop-off points, and suspected hallucinations.

#### Scenario: Consensus jobs identified
- **WHEN** a job title appears in results from two or more models (fuzzy title match)
- **THEN** it SHALL be counted as a consensus job

#### Scenario: Model-unique jobs flagged
- **WHEN** a job title appears in exactly one model's results
- **THEN** it SHALL be listed as unique to that model for manual review

#### Scenario: Pagination drop-off reported
- **WHEN** models return different page counts
- **THEN** the judge SHALL note at which page each model stopped and flag any model that stopped before the maximum observed page count

### Requirement: Judge uses a fixed model
The `TuneJudge` SHALL always use `claude-sonnet-4-6` regardless of which models are being evaluated. The judge model is not configurable at runtime.

#### Scenario: Judge model is fixed
- **WHEN** the runner invokes the judge
- **THEN** the judge SHALL use `claude-sonnet-4-6` unconditionally

### Requirement: Judge output is structured via Pydantic model
The judge's response SHALL be parsed into a typed Pydantic output model, not free-form text, so downstream consumers (log writer, console printer) can access fields programmatically.

#### Scenario: Structured output accessible after judge run
- **WHEN** the judge completes
- **THEN** the runner SHALL access `judge_result.consensus_count`, `judge_result.model_unique`, `judge_result.pagination_analysis`, and `judge_result.summary` as typed fields
