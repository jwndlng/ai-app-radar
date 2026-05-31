# Spec: Log Retention

## Purpose

Controls how many JSONL log files are retained per flow. After each run, `RunLogger` prunes the oldest log files so that the `logs/` directory does not grow unboundedly.

## Requirements

### Requirement: RunLogger prunes old log files after each run
After closing the current log file, `RunLogger.finish()` SHALL delete the oldest log files
for the current flow so that at most `keep` files remain in the `logs/` directory.
The default value of `keep` SHALL be 10.

#### Scenario: Fewer than keep files exist
- **WHEN** `finish()` is called and the number of `<flow>_*.jsonl` files in `logs/` is less than or equal to `keep`
- **THEN** no files SHALL be deleted

#### Scenario: More than keep files exist
- **WHEN** `finish()` is called and the number of `<flow>_*.jsonl` files in `logs/` exceeds `keep`
- **THEN** the oldest files (by filename sort order) SHALL be deleted until exactly `keep` files remain

#### Scenario: Current run's file is always retained
- **WHEN** pruning runs after a completed run
- **THEN** the file written during that run SHALL be among the retained files

#### Scenario: Other flows are unaffected
- **WHEN** pruning runs for flow `scout`
- **THEN** files matching `enrich_*.jsonl`, `evaluate_*.jsonl`, or any other flow pattern SHALL NOT be deleted

### Requirement: RunLogger accepts a configurable retention limit
`RunLogger.__init__` SHALL accept a `keep` parameter (type `int`, default `10`) that controls
how many log files are retained per flow after each run.

#### Scenario: Default retention limit applied
- **WHEN** `RunLogger` is instantiated without a `keep` argument
- **THEN** at most 10 log files SHALL be retained for that flow after `finish()` is called

#### Scenario: Custom retention limit applied
- **WHEN** `RunLogger` is instantiated with `keep=N`
- **THEN** at most N log files SHALL be retained for that flow after `finish()` is called
