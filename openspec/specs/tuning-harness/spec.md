# Specification: Tuning Harness Capability

## Purpose
To evaluate and compare WebsearchProvider behaviour across multiple LLM models for a given company, producing scored results and a judge analysis.

## Requirements

### Requirement: Runner executes one WebsearchProvider run per model
The `TuneRunner` SHALL execute `WebsearchProvider.scout()` once per model defined in the case file, sequentially, collecting the full job list and page count for each run.

#### Scenario: All models run against the same company config
- **WHEN** a tune case specifies models `[flash, sonnet]`
- **THEN** the runner SHALL call `WebsearchProvider.scout()` twice with the same company config, each time with a different model injected

#### Scenario: Sequential execution
- **WHEN** multiple models are configured
- **THEN** each model run SHALL complete before the next begins

### Requirement: Runner scores each model against expected outcomes
For each model run the runner SHALL compute a pass/fail score against the case's `expected_pages`, `jobs_min`, and `jobs_max` fields.

#### Scenario: Model meets expected page count and job range
- **WHEN** a model traverses exactly `expected_pages` pages and finds a job count within `[jobs_min, jobs_max]`
- **THEN** the run SHALL be scored as passing on both dimensions

#### Scenario: Model misses expected page count
- **WHEN** a model stops paginating before reaching `expected_pages`
- **THEN** the pages dimension SHALL be scored as failing, noting the actual page count reached

#### Scenario: Job count outside expected range
- **WHEN** a model finds fewer than `jobs_min` or more than `jobs_max` jobs
- **THEN** the jobs dimension SHALL be scored as failing, noting the actual count

### Requirement: Runner writes a JSONL result log
The runner SHALL append a JSONL result file to `tuning/results/<company>_<timestamp>.jsonl` containing per-model raw job lists, scores, elapsed time, and the judge's analysis.

#### Scenario: Result file created on each run
- **WHEN** a tune run completes
- **THEN** a new JSONL file SHALL exist at `tuning/results/<company>_<timestamp>.jsonl`

#### Scenario: Per-model record written before judge
- **WHEN** all model runs are complete
- **THEN** the log SHALL contain one record per model with its job list, page count, score, and elapsed seconds before the judge record is appended

### Requirement: Runner prints a comparison table to stdout
After all model runs the runner SHALL print a formatted table showing model, pages, jobs, pass/fail on each dimension, and elapsed time.

#### Scenario: Table printed on completion
- **WHEN** all model runs and the judge have completed
- **THEN** a table SHALL be printed with one row per model plus a judge summary row
