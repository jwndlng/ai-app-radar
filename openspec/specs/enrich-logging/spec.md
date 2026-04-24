# enrich-logging Specification

## Purpose
Defines the logging contract for the enrich flow — colored console output, JSONL log file, and per-job event mapping via `RunLogger`.

## Requirements

### Requirement: EnrichOrchestrator uses RunLogger for console and file output
`EnrichOrchestrator` SHALL instantiate `RunLogger("enrich", root_dir)` and use it for all
console output and log file writing, replacing all `print()` calls.

#### Scenario: Run header emitted on start
- **WHEN** `run()` is called with N enrichable jobs
- **THEN** `log.start(total=N)` SHALL be called before any worker begins processing

#### Scenario: No jobs produces a warning and exits
- **WHEN** there are no jobs with state `"discovered"`
- **THEN** `log.item_warn` or equivalent SHALL be used to signal the empty state and the run SHALL end without a log file with zero items

#### Scenario: Run summary emitted on finish
- **WHEN** all workers have completed
- **THEN** `log.finish()` SHALL be called and a `logs/enrich_<ts>.jsonl` file SHALL exist

### Requirement: Per-job outcomes mapped to RunLogger events
Each enrichment outcome SHALL be recorded via the appropriate `RunLogger` method.

#### Scenario: Job enriched successfully
- **WHEN** `EnrichAgent.extract()` returns valid data and the job state is set to `"parsed"`
- **THEN** `log.item_ok(name, label="enrich", detail="parsed", elapsed=...)` SHALL be called

#### Scenario: Page fetch failed or soft 404
- **WHEN** the enriched result contains a `_fetch_error` key
- **THEN** `log.item_warn(name, label="enrich", detail=reason, elapsed=...)` SHALL be called

#### Scenario: Unexpected exception raised
- **WHEN** an exception is raised during job processing
- **THEN** `log.item_fail(name, label="enrich", error=exc, tb=traceback.format_exc(), elapsed=...)` SHALL be called

### Requirement: Worker ID retained in JSONL, absent from console
The `worker_id` integer SHALL not appear in the console output. It SHALL be passed as an
extra kwarg to each `RunLogger` call so it is present in the JSONL record.

#### Scenario: Worker ID in log record
- **WHEN** a worker emits any item event
- **THEN** the JSONL record SHALL contain a `worker_id` field with the worker's integer ID

#### Scenario: Worker ID not in console line
- **WHEN** a worker emits any item event
- **THEN** the console output SHALL not contain `[Worker N]` or any worker identifier

### Requirement: Cooldown and gap-wait delays are silent
Internal rate-limiting waits (start-gap and cooldown breaks) SHALL NOT produce any
console output or log events.

#### Scenario: Cooldown wait is silent
- **WHEN** the orchestrator enters a cooldown pause between batches
- **THEN** no print or log call SHALL occur during the wait
