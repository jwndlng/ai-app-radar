# evaluate-logging Specification

## Purpose
Defines the logging contract for the evaluate flow — colored console output, JSONL log file, per-job elapsed timing, and outcome event mapping via `RunLogger`.

## Requirements

### Requirement: EvaluateOrchestrator uses RunLogger for console and file output
`EvaluateOrchestrator` SHALL instantiate `RunLogger("evaluate", root_dir)` and use it for
all console output and log file writing, replacing all `print()` calls.

#### Scenario: Run header emitted on start
- **WHEN** `run()` is called
- **THEN** the count of jobs with state `"parsed"` SHALL be computed upfront and passed to `log.start(total=N)` before the evaluation loop begins

#### Scenario: No parsed jobs produces a warning and exits
- **WHEN** no jobs have state `"parsed"`
- **THEN** `log.item_warn` or equivalent SHALL signal the empty state and the run SHALL end

#### Scenario: Run summary emitted on finish
- **WHEN** the evaluation loop completes
- **THEN** `log.finish()` SHALL be called and a `logs/evaluate_<ts>.jsonl` file SHALL exist

### Requirement: Per-job outcomes mapped to RunLogger events
Each evaluation outcome SHALL be recorded via the appropriate `RunLogger` method. Elapsed
time SHALL be measured per job using `time.monotonic()`.

#### Scenario: Job auto-matched or queued for review
- **WHEN** a job's score meets auto-match threshold or falls in the review range
- **THEN** `log.item_ok(name, label="evaluate", detail="score N/10 → <status>", elapsed=...)` SHALL be called

#### Scenario: Job pre-filter rejected
- **WHEN** `Vetter.vet()` returns `(False, reason)`
- **THEN** `log.item_warn(name, label="evaluate", detail=reason, elapsed=...)` SHALL be called

#### Scenario: Job auto-rejected by score
- **WHEN** a job's score falls below the auto-reject threshold
- **THEN** `log.item_warn(name, label="evaluate", detail="score N/10 below threshold", elapsed=...)` SHALL be called

#### Scenario: Fit scoring failed
- **WHEN** the LLM fit scoring call raises an exception or returns an invalid result
- **THEN** `log.item_fail(name, label="evaluate", error=<exception>, elapsed=...)` SHALL be called
